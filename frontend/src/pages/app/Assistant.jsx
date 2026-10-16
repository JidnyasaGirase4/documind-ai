import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { MessageSquareText, PanelLeft, Plus, Sparkles, Trash2 } from 'lucide-react'
import { Button } from '../../components/common/Button'
import { ConfirmDialog } from '../../components/common/ConfirmDialog'
import { ErrorState } from '../../components/common/ErrorState'
import { Skeleton } from '../../components/common/LoadingSkeleton'
import { ChatMessage } from '../../components/chat/ChatMessage'
import { ChatComposer } from '../../components/chat/ChatComposer'
import { DocumentSelector } from '../../components/chat/DocumentSelector'
import { CitationViewer } from '../../components/viewer/CitationViewer'
import { useAsync } from '../../hooks/useAsync'
import { useDocumentTitle } from '../../hooks/useDocumentTitle'
import { useToast } from '../../context/ToastContext'
import { conversationService, documentService } from '../../services'
import { cx, formatDateTime, formatRelative } from '../../utils/format'

// Questions that make sense for any document (the assistant answers these from the start of the document).
const EXAMPLES = ['Summarize this document in a few sentences.', 'What are the key points?', 'What is this document about?']

export default function Assistant() {
  useDocumentTitle('AI Assistant')
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()

  const [messages, setMessages] = useState([])
  const [conversation, setConversation] = useState(null)
  const [loadingConv, setLoadingConv] = useState(false)
  const [loadError, setLoadError] = useState(null)
  const [sending, setSending] = useState(false)
  const [selectedDocs, setSelectedDocs] = useState([])
  const [panelOpen, setPanelOpen] = useState(false)
  const [toDelete, setToDelete] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [viewer, setViewer] = useState(null) // { citations, index } while the PDF viewer is open

  const composerRef = useRef(null)
  const logEndRef = useRef(null)
  const skipLoadFor = useRef(null)
  const loadSeq = useRef(0)
  const tmpId = useRef(0)
  const sendingRef = useRef(false)

  const readyDocs = useAsync(async () => (await documentService.listDocuments({ pageSize: 100, status: 'ready', scope: 'all' })).items, [])
  const convList = useAsync(async () => (await conversationService.listConversations({ pageSize: 30 })).items, [])

  const loadConversation = useCallback(async (id) => {
    const seq = ++loadSeq.current
    setLoadingConv(true)
    setLoadError(null)
    try {
      const conv = await conversationService.getConversation(id)
      if (seq !== loadSeq.current) return
      setConversation(conv)
      setMessages(conv.messages ?? [])
    } catch (err) {
      if (seq === loadSeq.current) setLoadError(err)
    } finally {
      if (seq === loadSeq.current) setLoadingConv(false)
    }
  }, [])

  useEffect(() => {
    setPanelOpen(false)
    if (!conversationId) {
      loadSeq.current += 1
      setMessages([])
      setConversation(null)
      setLoadError(null)
      setLoadingConv(false)
      return
    }
    if (String(skipLoadFor.current) === String(conversationId)) {
      skipLoadFor.current = null
      return
    }
    loadConversation(conversationId)
  }, [conversationId, loadConversation])

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [messages, sending])

  const ensureConversation = async () => {
    if (conversationId) return conversationId
    const conv = await conversationService.createConversation({ documentIds: selectedDocs })
    skipLoadFor.current = conv.id
    setConversation(conv)
    navigate(`/app/assistant/${conv.id}`, { replace: true })
    return conv.id
  }

  const send = async (text, retryOf) => {
    if (sendingRef.current) return
    sendingRef.current = true
    setSending(true)
    const localId = retryOf?.id ?? `tmp-${++tmpId.current}`
    const optimistic = { id: localId, role: 'user', content: text, citations: [], status: 'sending', createdAt: new Date().toISOString() }
    setMessages((m) => (retryOf ? m.map((x) => (x.id === localId ? optimistic : x)) : [...m, optimistic]))
    try {
      const convId = await ensureConversation()
      const { userMessage, assistantMessage } = await conversationService.sendMessage(convId, { content: text, documentIds: selectedDocs })
      setMessages((m) => [...m.map((x) => (x.id === localId ? (userMessage ?? { ...x, status: undefined }) : x)), assistantMessage])
      setConversation((c) => (c ? { ...c, updatedAt: assistantMessage.createdAt ?? new Date().toISOString() } : c))
      convList.reload({ silent: true })
      // The server sets the conversation title from the first question; pick it up for the header.
      conversationService
        .getConversation(convId)
        .then((c) => setConversation((prev) => (prev ? { ...prev, title: c.title, updatedAt: c.updatedAt } : prev)))
        .catch(() => {})
    } catch (err) {
      setMessages((m) => m.map((x) => (x.id === localId ? { ...x, status: 'failed', error: err.message } : x)))
    } finally {
      sendingRef.current = false
      setSending(false)
      composerRef.current?.focus()
    }
  }

  const copy = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Answer copied to clipboard.')
    } catch {
      toast.error('Could not copy. Select the text and copy it manually.')
    }
  }

  const patchMessage = (id, feedback) => setMessages((m) => m.map((x) => (x.id === id ? { ...x, feedback } : x)))
  const giveFeedback = async (msg, f) => {
    patchMessage(msg.id, await conversationService.setFeedback(conversationId ?? conversation?.id, msg.id, f))
  }
  const removeFeedback = async (msg) => {
    await conversationService.clearFeedback(conversationId ?? conversation?.id, msg.id)
    patchMessage(msg.id, null)
  }

  const openCitation = (c, all) => {
    const list = all?.length ? all : [c]
    setViewer({ citations: list, index: Math.max(0, list.indexOf(c)) })
  }

  const confirmDelete = async () => {
    setDeleting(true)
    try {
      if (toDelete.all) {
        // Deletes every chat in the list (the list shows the most recent 30; repeat if there are more).
        const ids = (convList.data ?? []).map((c) => c.id)
        await Promise.all(ids.map((id) => conversationService.deleteConversation(id)))
        toast.success('All conversations deleted.')
        setToDelete(null)
        convList.reload({ silent: true })
        if (conversationId) navigate('/app/assistant', { replace: true })
        return
      }
      await conversationService.deleteConversation(toDelete.id)
      toast.success('Conversation deleted.')
      const wasOpen = String(toDelete.id) === String(conversationId)
      setToDelete(null)
      convList.reload({ silent: true })
      if (wasOpen) navigate('/app/assistant', { replace: true })
    } catch (err) {
      toast.error(err.message)
    } finally {
      setDeleting(false)
    }
  }

  const docs = readyDocs.data ?? []
  const noReadyDocs =!readyDocs.loading && !readyDocs.error && docs.length === 0

  const list = (
    <div className="flex h-full flex-col">
      <div className="p-3">
        <Button to="/app/assistant" variant="secondary" className="w-full">
          <Plus className="h-4 w-4" aria-hidden="true" />
          New chat
        </Button>
      </div>
      <nav aria-label="Conversations" className="flex-1 overflow-y-auto px-2 pb-3">
        {convList.loading && (
          <div className="space-y-2 p-1">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        )}
        {convList.error && (
          <div className="p-2 text-sm text-danger">
            Could not load conversations.{' '}
            <button type="button" className="font-medium underline" onClick={() => convList.reload()}>
              Retry
            </button>
          </div>
        )}
        {convList.data?.length === 0 && <p className="px-2 py-3 text-sm text-muted">No conversations yet.</p>}
        {convList.data?.length > 1 && (
          <button
            type="button"
            onClick={() => setToDelete({ all: true })}
            className="mb-1 flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs font-medium text-muted hover:bg-danger-soft hover:text-danger"
          >
            <Trash2 className="h-3.5 w-3.5" aria-hidden="true" />
            Delete all chats
          </button>
        )}
        <ul className="space-y-0.5">
          {convList.data?.map((c) => (
            <li key={c.id} className="group relative">
              <Link
                to={`/app/assistant/${c.id}`}
                aria-current={String(c.id) === conversationId ? 'page' : undefined}
                className={cx(
                  'block rounded-control py-2 pl-3 pr-10 text-sm',
                  String(c.id) === conversationId ? 'bg-brand-50 font-medium text-brand-700' : 'text-ink hover:bg-stone-50',
                )}
              >
                <span className="block truncate">{c.title}</span>
                <span className="block text-xs font-normal text-muted">{formatRelative(c.updatedAt)}</span>
              </Link>
              <button
                type="button"
                onClick={() => setToDelete(c)}
                aria-label={`Delete conversation ${c.title}`}
                title="Delete this chat"
                className="absolute right-1.5 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted opacity-100 transition-opacity hover:bg-danger-soft hover:text-danger focus-visible:opacity-100 lg:opacity-0 lg:group-hover:opacity-100"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  )

  return (
    <div className="flex h-[calc(100dvh-7.5rem)] min-h-[420px] overflow-hidden rounded-card border border-line bg-surface shadow-card">
      <aside className={cx('w-full shrink-0 border-r border-line bg-surface lg:block lg:w-72', panelOpen ? 'block' : 'hidden')} aria-label="Conversation list">
        {list}
      </aside>

      <section className={cx('min-w-0 flex-1 flex-col bg-canvas', panelOpen ? 'hidden lg:flex' : 'flex')} aria-label="Chat">
        <div className="flex flex-wrap items-center gap-3 border-b border-line bg-surface px-4 py-3">
          <button
            type="button"
            onClick={() => setPanelOpen(true)}
            aria-label="Show conversations"
            className="rounded-md p-1.5 text-ink hover:bg-stone-100 lg:hidden"
          >
            <PanelLeft className="h-5 w-5" />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="truncate text-sm font-semibold text-ink">{conversation?.title ?? 'New conversation'}</h1>
            {conversation?.updatedAt && <p className="text-xs text-muted">Updated {formatDateTime(conversation.updatedAt)}</p>}
          </div>
          <div className="w-full sm:w-auto">
            <DocumentSelector documents={docs} selected={selectedDocs} onChange={setSelectedDocs} disabled={sending} />
          </div>
        </div>

        {selectedDocs.length > 1 && (
          <div className="flex flex-wrap items-center gap-2 border-b border-line bg-brand-50/60 px-4 py-2 text-xs text-brand-800" data-testid="multi-doc-banner">
            <span className="font-medium">Comparing {selectedDocs.length} documents:</span>
            {selectedDocs.map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setSelectedDocs((cur) => cur.filter((x) => x !== id))}
                disabled={sending}
                title="Remove from this question"
                className="inline-flex max-w-[14rem] items-center gap-1 rounded-full border border-brand-200 bg-surface px-2.5 py-0.5 hover:bg-brand-100 disabled:opacity-60"
              >
                <span className="truncate">{docs.find((d) => d.id === id)?.filename ?? `Document ${id}`}</span>
                <span aria-hidden="true">×</span>
                <span className="sr-only">Remove</span>
              </button>
            ))}
            <span className="text-muted">Each answer cites its document and page; conflicts between documents are called out.</span>
          </div>
        )}

        <div className="flex-1 overflow-y-auto px-4 py-5" role="log" aria-live="polite" aria-label="Conversation messages">
          {loadingConv ? (
            <div className="space-y-4" role="status" aria-label="Loading conversation">
              <Skeleton className="ml-auto h-10 w-2/3" />
              <Skeleton className="h-24 w-3/4" />
            </div>
          ) : loadError ? (
            <ErrorState
              error={loadError}
              title={loadError.status === 404 ? 'Conversation not found' : undefined}
              onRetry={loadError.status === 404 ? undefined : () => loadConversation(conversationId)}
            />
          ) : messages.length === 0 ? (
            <div className="mx-auto flex max-w-xl flex-col items-center py-8 text-center">
              <span className="icon-tile mb-4 h-12 w-12 animate-float !rounded-xl">
                <Sparkles className="h-6 w-6" aria-hidden="true" />
              </span>
              <h2 className="text-lg font-bold text-ink">Ask anything about your documents</h2>
              <p className="mt-1 text-sm text-muted">Answers include the document and page they are based on, so you can check the source.</p>
              {readyDocs.error ? (
                <p className="mt-4 text-sm text-danger">Could not load your documents: {readyDocs.error.message}</p>
              ) : noReadyDocs ? (
                <div className="mt-5 rounded-card border border-line bg-surface p-4 text-sm">
                  <p className="text-ink">You need at least one processed PDF before you can ask questions.</p>
                  <Button to="/app/documents" className="mt-3">
                    Go to My Documents
                  </Button>
                </div>
              ) : (
                <div className="mt-6 flex w-full flex-col gap-2" role="group" aria-label="Example questions">
                  {EXAMPLES.map((q) => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => send(q)}
                      disabled={sending}
                      className="flex items-center gap-2 rounded-xl border border-line bg-surface px-4 py-3.5 text-left text-sm font-medium text-ink shadow-card transition-all hover:-translate-y-0.5 hover:border-brand-300 hover:bg-brand-50 hover:shadow-lift disabled:opacity-60"
                    >
                      <MessageSquareText className="h-4 w-4 shrink-0 text-brand-600" aria-hidden="true" />
                      {q}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="mx-auto max-w-3xl space-y-6">
              {messages.map((m, i) => (
                <ChatMessage
                  key={m.id ?? i}
                  message={m}
                  onCopy={m.role === 'assistant' ? copy : undefined}
                  onRetry={(msg) => send(msg.content, msg)}
                  onOpenCitation={openCitation}
                  onFeedback={m.role === 'assistant' ? giveFeedback : undefined}
                  onClearFeedback={removeFeedback}
                  onFollowUp={i === messages.length - 1 && !sending ? (q) => send(q) : undefined}
                />
              ))}
              {sending && (
                <div className="flex animate-fade-in items-center gap-3 text-sm text-muted" role="status">
                  <span className="flex items-center gap-1 rounded-2xl border border-line bg-surface px-4 py-3 shadow-card" aria-hidden="true">
                    {[0, 1, 2].map((i) => (
                      <span key={i} className="h-2 w-2 animate-dot-bounce rounded-full bg-brand-500" style={{ animationDelay: `${i * 160}ms` }} />
                    ))}
                  </span>
                  Searching your documents…
                </div>
              )}
            </div>
          )}
          <div ref={logEndRef} />
        </div>

        <div className="border-t border-line bg-canvas px-4 py-3">
          <div className="mx-auto max-w-3xl">
            <ChatComposer
              ref={composerRef}
              onSend={(t) => send(t)}
              sending={sending}
              disabled={loadingConv || Boolean(loadError) || noReadyDocs}
            />
          </div>
        </div>
      </section>

      <CitationViewer
        open={Boolean(viewer)}
        onClose={() => setViewer(null)}
        citations={viewer?.citations ?? []}
        index={viewer?.index ?? 0}
        onIndexChange={(i) => setViewer((v) => (v ? { ...v, index: i } : v))}
      />

      <ConfirmDialog
        open={Boolean(toDelete)}
        title={toDelete?.all ? 'Delete all chats?' : 'Delete this chat?'}
        description={
          toDelete?.all
            ? `All ${convList.data?.length ?? ''} conversations and their messages will be permanently removed. Your documents are not affected.`
            : toDelete
              ? `"${toDelete.title}" and all of its messages will be permanently removed.`
              : ''
        }
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => setToDelete(null)}
      />
    </div>
  )
}
