// True only in the public demo build (npm run build:demo). In every other build this is a compile-time `false`, so the demo
// engine and its sample data are not part of the bundle.
export const DEMO = import.meta.env.VITE_DEMO === '1'
export const DEMO_EMAIL = 'demo@example.com'
export const DEMO_PASSWORD = 'DocuMind2026'
