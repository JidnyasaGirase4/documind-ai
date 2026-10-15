export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')
export const API_PREFIX = '/api/v1'
export const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB) || 25
export const MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
export const ACCEPTED_TYPE_LABEL = 'PDF'
export const TOKEN_STORAGE_KEY = 'documind.token'
export const DOCUMENT_POLL_INTERVAL_MS = 5000
