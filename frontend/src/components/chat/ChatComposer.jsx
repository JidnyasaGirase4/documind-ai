import { forwardRef, useImperativeHandle, useRef, useState } from 'react'
import { Loader2, Send } from 'lucide-react'

const MAX_LENGTH = 4000

// Enter sends, Shift+Enter inserts a newline; the Send button is always available
// as the accessible alternative. Focus returns to the textarea after sending.
export const ChatComposer = forwardRef(function ChatComposer({ onSend, sending, disabled, placeholder }, ref) {
  const [value, setValue] = useState('')
  const textareaRef = useRef(null)

  useImperativeHandle(ref, () => ({
    focus: () => textareaRef.current?.focus(),
    setValue: (v) => {
      setValue(v)
      textareaRef.current?.focus()
    },
  }))

  const trimmed = value.trim()
  const canSend = trimmed.length > 0 && !sending && !disabled

  const submit = async () => {
    if (!canSend) return
    const text = trimmed
    setValue('')
    await onSend(text)
    textareaRef.current?.focus()
  }

  const autosize = (el) => {
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
      className="rounded-card border border-line bg-surface p-2 shadow-card focus-within:border-brand-600"
    >
      <label htmlFor="chat-input" className="sr-only">
        Ask a question about your documents
      </label>
      <textarea
        id="chat-input"
        ref={textareaRef}
        rows={1}
        value={value}
        maxLength={MAX_LENGTH}
        disabled={disabled}
        placeholder={placeholder || 'Ask about your documents…'}
        aria-describedby="chat-input-hint"
        onChange={(e) => {
          setValue(e.target.value)
          autosize(e.target)
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault()
            submit()
          }
        }}
        className="max-h-[180px] w-full resize-none bg-transparent px-2 py-2 text-sm text-ink placeholder:text-stone-400 focus:outline-none"
      />
      <div className="flex items-center justify-between gap-3 px-1 pb-0.5">
        <p id="chat-input-hint" className="hidden text-xs text-muted sm:block">
          Enter to send · Shift+Enter for a new line
        </p>
        <button
          type="submit"
          disabled={!canSend}
          aria-label="Send message"
          className="ml-auto inline-flex h-9 items-center gap-2 rounded-control bg-brand-600 px-4 text-sm font-medium text-white hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-600/50"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Send className="h-4 w-4" aria-hidden="true" />}
          Send
        </button>
      </div>
    </form>
  )
})
