import { describe, expect, it, vi, beforeEach } from 'vitest'
import { screen, waitFor, within, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from './utils'
import { DocumentReviewPanel } from '../components/reviews/DocumentReviewPanel'
import { FindingList } from '../components/reviews/ConflictFindings'
import { AnalyzeButton } from '../components/reviews/AnalyzeButton'
import { dueText } from '../components/reviews/reviewMeta'
import ReviewCenter from '../pages/app/ReviewCenter'
import { conflictService, knowledgeService, reviewService } from '../services'

vi.mock('../services', async () => {
  const actual = await vi.importActual('../services')
  return {
    ...actual,
    reviewService: { getReview: vi.fn(), getHistory: vi.fn(), saveSchedule: vi.fn(), clearSchedule: vi.fn(), startReview: vi.fn(), completeReview: vi.fn(), getSummary: vi.fn(), listReviews: vi.fn() },
    conflictService: { analyze: vi.fn(), getReport: vi.fn(), listFindings: vi.fn(), decide: vi.fn(), getDecisions: vi.fn() },
    knowledgeService: { listCollections: vi.fn() },
  }
})

const iso = (days) => new Date(Date.now() + days * 86400000).toISOString().slice(0, 10)
const review = (o) => ({ documentId: 1, title: 'policy.pdf', versionNumber: 2, status: 'upcoming', intervalDays: 90, nextReviewDate: iso(30), daysUntilDue: 30, assignedReviewer: null, notes: null, inReview: false, lastReviewedAt: '2026-09-01T10:00:00Z', lastReviewedBy: { id: 1, name: 'Olivia' }, lastOutcome: 'approved', lastReviewedVersion: 1, versionChanged: false, role: 'owner', ...o })
const entry = (o) => ({ id: 1, documentId: 1, versionNumber: 1, reviewer: { id: 1, name: 'Olivia' }, reviewedAt: '2026-09-01T10:00:00Z', outcome: 'approved', notes: 'Checked against law', previousDate: iso(-1), nextDate: iso(30), ...o })
const pageOf = (items) => ({ items, total: items.length, page: 1, pageSize: 10, pages: 1 })
const src = (o) => ({ documentId: 1, title: 'a.pdf', versionId: 11, versionNumber: 1, isCurrent: true, page: 2, chunkId: 'chunk-5', excerpt: 'Records must be retained for seven years.', ...o })
const finding = (o) => ({ id: 3, reportId: 1, kind: 'cross_document', type: 'value_mismatch', assessment: 'potential_conflict', explanation: 'Seven versus three years.', quotesVerified: true, a: src(), b: src({ documentId: 2, title: 'b.pdf', versionId: 22, versionNumber: 3, isCurrent: false, chunkId: 'chunk-9', excerpt: 'Records must be retained for three years.' }), stale: true, reviewStatus: 'pending', reviewedBy: null, reviewedAt: null, reviewNote: null, detectedAt: '2026-10-01T10:00:00Z', canDecide: true, ...o })

beforeEach(() => {
  vi.clearAllMocks()
  reviewService.getReview.mockResolvedValue(review())
  reviewService.getHistory.mockResolvedValue(pageOf([entry()]))
  knowledgeService.listCollections.mockResolvedValue({ items: [{ id: 5, name: 'Policies', role: 'owner' }, { id: 6, name: 'Shared', role: 'viewer' }], total: 2, page: 1, pageSize: 100, pages: 1 })
})

describe('dueText', () => {
  it('words the distance to the date', () => {
    expect(dueText({ nextReviewDate: null })).toBe('No review date')
    expect(dueText({ nextReviewDate: 'x', daysUntilDue: 0 })).toBe('Due today')
    expect(dueText({ nextReviewDate: 'x', daysUntilDue: -1 })).toBe('1 day overdue')
    expect(dueText({ nextReviewDate: 'x', daysUntilDue: 5 })).toBe('Due in 5 days')
  })
})

describe('DocumentReviewPanel', () => {
  it('shows status, dates, last reviewer, version and the review history', async () => {
    reviewService.getReview.mockResolvedValue(review({ status: 'overdue', daysUntilDue: -3, versionChanged: true }))
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage />, { withAuth: false })
    expect(await screen.findByText('Overdue')).toBeInTheDocument()
    expect(screen.getByText(/3 days overdue/)).toBeInTheDocument()
    expect(screen.getByText(/by Olivia · version 1/)).toBeInTheDocument()
    expect(screen.getByText(/A newer version \(version 2\) has been uploaded since the last review \(version 1\)/)).toBeInTheDocument()
    const list = await screen.findByRole('list', { name: /review history/i })
    expect(within(list).getByText('Approved as current')).toBeInTheDocument()
    expect(within(list).getByText('Checked against law')).toBeInTheDocument()
  })

  it('viewers can read but not change anything', async () => {
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage={false} />, { withAuth: false })
    await screen.findByText('Upcoming')
    for (const name of [/schedule/i, /complete review/i, /start review/i, /remove schedule/i]) expect(screen.queryByRole('button', { name })).not.toBeInTheDocument()
  })

  it('validates and saves a schedule', async () => {
    reviewService.saveSchedule.mockResolvedValue(review())
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Edit schedule' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText('Next review date'), { target: { value: iso(-2) } })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save schedule' }))
    expect(await within(dialog).findByText('The review date must be today or later.')).toBeInTheDocument()
    fireEvent.change(within(dialog).getByLabelText('Next review date'), { target: { value: '' } })
    const interval = within(dialog).getByLabelText('Repeat every (days)')
    await userEvent.clear(interval)
    await userEvent.type(interval, '0')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save schedule' }))
    expect(await within(dialog).findByText(/between 1 and 3650/)).toBeInTheDocument()
    expect(reviewService.saveSchedule).not.toHaveBeenCalled()
    await userEvent.click(within(dialog).getByRole('button', { name: '180 days' }))
    fireEvent.change(within(dialog).getByLabelText('Next review date'), { target: { value: iso(10) } })
    await userEvent.click(within(dialog).getByRole('button', { name: 'Save schedule' }))
    await waitFor(() => expect(reviewService.saveSchedule).toHaveBeenCalledWith(1, { intervalDays: 180, nextReviewDate: iso(10), notes: null }))
  })

  it('completes a review with an outcome and notes', async () => {
    reviewService.completeReview.mockResolvedValue(review())
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Complete review' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('recorded under your name')
    await userEvent.selectOptions(within(dialog).getByLabelText('Outcome'), 'outdated')
    await userEvent.type(within(dialog).getByLabelText(/review notes/i), 'Superseded by 2026 rules')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record review' }))
    await waitFor(() => expect(reviewService.completeReview).toHaveBeenCalledWith(1, { outcome: 'outdated', notes: 'Superseded by 2026 rules', nextReviewDate: undefined }))
  })

  it('shows the server message if recording fails, and an error state when loading fails', async () => {
    reviewService.completeReview.mockRejectedValue(new Error('You need editor access to do that.'))
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Complete review' }))
    const dialog = await screen.findByRole('dialog')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record review' }))
    expect(await within(dialog).findByText('You need editor access to do that.')).toBeInTheDocument()
  })

  it('asks before removing a schedule', async () => {
    reviewService.clearSchedule.mockResolvedValue(review({ status: 'reviewed', nextReviewDate: null }))
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: 'Remove schedule' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('history is kept')
    expect(reviewService.clearSchedule).not.toHaveBeenCalled()
    await userEvent.click(within(dialog).getByRole('button', { name: 'Remove schedule' }))
    await waitFor(() => expect(reviewService.clearSchedule).toHaveBeenCalledWith(1))
  })

  it('shows an error state with retry', async () => {
    reviewService.getReview.mockRejectedValueOnce(new Error('Server unavailable')).mockResolvedValue(review())
    renderWithProviders(<DocumentReviewPanel documentId={1} canManage />, { withAuth: false })
    expect(await screen.findByText(/Server unavailable/)).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button', { name: /try again|retry/i })[0])
    expect(await screen.findByText('Upcoming')).toBeInTheDocument()
  })
})

describe('Review Center', () => {
  const summary = { today: iso(0), dueSoonDays: 14, scheduled: 5, upcoming: 2, due: 2, overdue: 1, inReview: 0, completed30: 4, recent: [{ documentId: 1, title: 'policy.pdf', versionNumber: 2, outcome: 'approved', reviewedAt: '2026-09-01T10:00:00Z', reviewer: { id: 1, name: 'Olivia' } }] }

  beforeEach(() => {
    reviewService.getSummary.mockResolvedValue(summary)
    reviewService.listReviews.mockResolvedValue(pageOf([review({ status: 'overdue', daysUntilDue: -2, title: 'late.pdf' }), review({ documentId: 2, title: 'soon.pdf', status: 'due', daysUntilDue: 4 })]))
  })

  it('shows real counts, rows with status, version and links, and recent reviews', async () => {
    renderWithProviders(<ReviewCenter />, { withAuth: false })
    const cards = await screen.findByLabelText('Review summary')
    expect(within(cards).getByText('5')).toBeInTheDocument()
    expect(within(cards).getByText('Overdue').previousSibling).toHaveTextContent('1')
    const list = await screen.findByRole('list', { name: 'Reviews' })
    expect(within(list).getByRole('link', { name: 'late.pdf' })).toHaveAttribute('href', '/app/documents/1')
    expect(within(list).getAllByText(/Version 2/)).toHaveLength(2)
    expect(within(list).getByText('Overdue')).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Recently completed reviews' })).toHaveTextContent('policy.pdf')
  })

  it('filters by clicking a summary card and by status select', async () => {
    renderWithProviders(<ReviewCenter />, { withAuth: false })
    await userEvent.click(await screen.findByRole('button', { name: /Overdue/ }))
    await waitFor(() => expect(reviewService.listReviews).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'overdue' })))
    await userEvent.selectOptions(screen.getByLabelText('Collection'), '5')
    await userEvent.click(screen.getByLabelText('Assigned to me'))
    await waitFor(() => expect(reviewService.listReviews).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'overdue', collectionId: '5', assignedToMe: true })))
  })

  it('has empty and error states', async () => {
    reviewService.listReviews.mockResolvedValueOnce(pageOf([])).mockRejectedValue(new Error('Boom'))
    renderWithProviders(<ReviewCenter />, { withAuth: false })
    expect(await screen.findByText('No reviews scheduled yet')).toBeInTheDocument()
    await userEvent.selectOptions(screen.getByLabelText('Status'), 'due')
    expect(await screen.findByText(/Boom/)).toBeInTheDocument()
  })

  it('switches to potential conflicts', async () => {
    conflictService.listFindings.mockResolvedValue(pageOf([finding()]))
    renderWithProviders(<ReviewCenter />, { withAuth: false })
    await userEvent.click(await screen.findByRole('tab', { name: 'Potential conflicts' }))
    expect(await screen.findByText('Seven versus three years.')).toBeInTheDocument()
    // only collections the user can edit may be analyzed
    const select = screen.getByLabelText('Collection to analyze')
    expect(within(select).queryByRole('option', { name: 'Shared' })).not.toBeInTheDocument()
    expect(within(select).getByRole('option', { name: 'Policies' })).toBeInTheDocument()
  })
})

describe('FindingList', () => {
  it('shows evidence from both sources with versions, labels it AI-assisted and links to the exact version and page', async () => {
    renderWithProviders(<FindingList findings={[finding()]} />, { withAuth: false })
    const a = screen.getByLabelText('Evidence Source A')
    const b = screen.getByLabelText('Evidence Source B')
    expect(within(a).getByText(/retained for seven years/)).toBeInTheDocument()
    expect(within(b).getByText(/retained for three years/)).toBeInTheDocument()
    expect(within(b).getByText('v3 (not current)')).toBeInTheDocument()
    expect(within(b).getByRole('link', { name: /b\.pdf/ })).toHaveAttribute('href', '/app/documents/2?page=2&chunk=chunk-9&version=22')
    expect(screen.getByText('Potential conflict')).toBeInTheDocument()
    expect(screen.getByText(/not a fact until a person confirms it/)).toBeInTheDocument()
    expect(screen.getByText(/Source changed · re-analyze/)).toBeInTheDocument()
    expect(screen.getByText('Awaiting review')).toBeInTheDocument()
  })

  it('distinguishes insufficient evidence', () => {
    renderWithProviders(<FindingList findings={[finding({ assessment: 'needs_review', quotesVerified: false, stale: false })]} />, { withAuth: false })
    expect(screen.getByText('Needs human review')).toBeInTheDocument()
    expect(screen.getByText(/quoted evidence could not be verified/)).toBeInTheDocument()
  })

  it('records a decision with a note', async () => {
    conflictService.decide.mockResolvedValue(finding({ reviewStatus: 'confirmed' }))
    const onChanged = vi.fn()
    renderWithProviders(<FindingList findings={[finding()]} onChanged={onChanged} />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: 'Confirm conflict' }))
    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('does not change either document')
    await userEvent.type(within(dialog).getByLabelText(/note/i), 'Legal confirmed')
    await userEvent.click(within(dialog).getByRole('button', { name: 'Record decision' }))
    await waitFor(() => expect(conflictService.decide).toHaveBeenCalledWith(3, 'confirmed', 'Legal confirmed'))
    await waitFor(() => expect(onChanged).toHaveBeenCalled())
  })

  it('hides the decision buttons from people who cannot decide', () => {
    renderWithProviders(<FindingList findings={[finding({ canDecide: false })]} />, { withAuth: false })
    expect(screen.queryByRole('button', { name: 'Confirm conflict' })).not.toBeInTheDocument()
    expect(screen.getByText(/Only editors of both documents can record a decision/)).toBeInTheDocument()
  })

  it('shows the recorded decision, who made it, and the history on demand', async () => {
    conflictService.getDecisions.mockResolvedValue([{ id: 1, decision: 'not_conflict', note: 'Different scope', decidedAt: '2026-10-02T10:00:00Z', decidedBy: { id: 1, name: 'Olivia' } }])
    renderWithProviders(<FindingList findings={[finding({ reviewStatus: 'not_conflict', reviewedBy: { id: 1, name: 'Olivia' }, reviewedAt: '2026-10-02T10:00:00Z', reviewNote: 'Different scope' })]} />, { withAuth: false })
    expect(screen.getByText(/Last decision by Olivia/)).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Decision history' }))
    expect(await screen.findByText(/Not a conflict/, { selector: 'strong' })).toBeInTheDocument()
  })

  it('has an empty state', () => {
    renderWithProviders(<FindingList findings={[]} />, { withAuth: false })
    expect(screen.getByText('No potential conflicts')).toBeInTheDocument()
  })
})

describe('AnalyzeButton', () => {
  it('starts an analysis and follows it to completion', async () => {
    conflictService.analyze.mockResolvedValue({ id: 9, status: 'running' })
    conflictService.getReport.mockResolvedValue({ id: 9, status: 'completed', passages: 4, pairs: 2, unparsed: 1, created: 1, error: null })
    const onDone = vi.fn()
    renderWithProviders(<AnalyzeButton documentId={1} onDone={onDone} />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: /Analyze for conflicts/ }))
    await waitFor(() => expect(conflictService.analyze).toHaveBeenCalledWith({ documentId: 1, collectionId: undefined }))
    expect(await screen.findByText(/Examined 4 passages and 2 candidate pairs; 1 AI answer could not be read and was ignored/)).toBeInTheDocument()
    expect(onDone).toHaveBeenCalled()
  })

  it('shows a failed analysis without technical details', async () => {
    conflictService.analyze.mockResolvedValue({ id: 9, status: 'running' })
    conflictService.getReport.mockResolvedValue({ id: 9, status: 'failed', error: 'The AI provider took too long to respond. Please try again.' })
    renderWithProviders(<AnalyzeButton documentId={1} />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: /Analyze for conflicts/ }))
    expect(await screen.findByRole('alert')).toHaveTextContent('took too long')
  })

  it('shows the error when it cannot start (for example no permission)', async () => {
    conflictService.analyze.mockRejectedValue(new Error('You need editor access to do that.'))
    renderWithProviders(<AnalyzeButton collectionId={5} label="Analyze collection" />, { withAuth: false })
    await userEvent.click(screen.getByRole('button', { name: 'Analyze collection' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('editor access')
  })
})
