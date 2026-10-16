import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './utils'
import { FeedbackControls } from '../components/chat/FeedbackControls'
import { QualityPanel } from '../components/analytics/QualityPanel'
import { dashboardService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    dashboardService: { getFeedbackStats: vi.fn(), getQueryStats: vi.fn(), getEvaluations: vi.fn() },
  }
})

beforeEach(() => vi.clearAllMocks())

describe('FeedbackControls', () => {
  it('sends a thumbs-up straight away and clears it on a second click', async () => {
    const onSubmit = vi.fn().mockResolvedValue()
    const onClear = vi.fn().mockResolvedValue()
    const { rerender } = renderWithProviders(<FeedbackControls feedback={null} onSubmit={onSubmit} onClear={onClear} />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: 'Good answer' }))
    expect(onSubmit).toHaveBeenCalledWith({ rating: 'up' })
    rerender(<FeedbackControls feedback={{ rating: 'up' }} onSubmit={onSubmit} onClear={onClear} />)
    await userEvent.click(screen.getByRole('button', { name: 'Good answer' }))
    await waitFor(() => expect(onClear).toHaveBeenCalledTimes(1))
  })

  it('collects a reason and note for a thumbs-down and shows save errors', async () => {
    const onSubmit = vi.fn().mockRejectedValueOnce(new Error('Server busy')).mockResolvedValueOnce()
    renderWithProviders(<FeedbackControls feedback={null} onSubmit={onSubmit} onClear={vi.fn()} />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: 'Bad answer' }))
    expect(onSubmit).not.toHaveBeenCalled() // the form opens first
    await userEvent.selectOptions(screen.getByLabelText(/what was wrong/i), 'wrong_source')
    await userEvent.type(screen.getByLabelText(/add a note/i), 'Wrong page')
    await userEvent.click(screen.getByRole('button', { name: 'Send feedback' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Server busy')
    await userEvent.click(screen.getByRole('button', { name: 'Send feedback' }))
    await waitFor(() => expect(onSubmit).toHaveBeenLastCalledWith({ rating: 'down', category: 'wrong_source', comment: 'Wrong page' }))
  })
})

describe('QualityPanel', () => {
  const empty = { days: 30, total: 0, up: 0, down: 0, satisfaction: null, by_day: [], down_categories: [], recent_comments: [] }
  const noQueries = { days: 30, total_questions: 0, latency_ms: { count: 0 }, latency_by_day: [], failure_categories: [] }

  it('shows honest empty states and does not invent evaluation results', async () => {
    dashboardService.getFeedbackStats.mockResolvedValue(empty)
    dashboardService.getQueryStats.mockResolvedValue(noQueries)
    dashboardService.getEvaluations.mockResolvedValue({ latest: null, history: [] })
    renderWithProviders(<QualityPanel />, { withAuth: false })
    expect(await screen.findByText('No evaluation has been run yet.')).toBeInTheDocument()
    expect(screen.getByText(/No feedback yet/)).toBeInTheDocument()
    expect(screen.getByText(/No questions recorded yet/)).toBeInTheDocument()
  })

  it('labels each evaluation metric with how it was obtained', async () => {
    dashboardService.getFeedbackStats.mockResolvedValue(empty)
    dashboardService.getQueryStats.mockResolvedValue(noQueries)
    dashboardService.getEvaluations.mockResolvedValue({
      latest: {
        id: 3, status: 'completed', dataset_name: 'ds', dataset_version: '1.0', k: 5, mode: 'full', started_at: '2026-01-01T00:00:00Z', finished_at: '2026-01-01T00:01:00Z',
        config: { embedding_model: 'minilm', llm_model: 'qwen' },
        metrics: {
          questions: 12,
          precision_at_k: { value: 0.4, kind: 'measured', n: 10, note: '' },
          faithfulness: { value: 0.8, kind: 'automated_estimate', n: 9, note: 'Lexical' },
        },
      },
      history: [],
    })
    renderWithProviders(<QualityPanel />, { withAuth: false })
    expect(await screen.findByText('40%')).toBeInTheDocument()
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getAllByText('Measured').length).toBeGreaterThan(1) // intro text + the metric badge
    expect(screen.getAllByText('Automated estimate').length).toBeGreaterThan(1)
  })

  it('shows an error state with retry when a section fails', async () => {
    dashboardService.getFeedbackStats.mockRejectedValue(new Error('boom'))
    dashboardService.getQueryStats.mockResolvedValue(noQueries)
    dashboardService.getEvaluations.mockResolvedValue({ latest: null, history: [] })
    renderWithProviders(<QualityPanel />, { withAuth: false })
    expect(await screen.findByText('Could not load this section')).toBeInTheDocument()
  })
})
