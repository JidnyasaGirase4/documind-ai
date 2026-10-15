import { useEffect } from 'react'

export function useDocumentTitle(title) {
  useEffect(() => {
    document.title = title ? `${title} · DocuMind AI` : 'DocuMind AI'
  }, [title])
}
