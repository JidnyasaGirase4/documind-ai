import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// `vite build --mode demo` builds the public GitHub Pages demo into ../docs/demo (relative base, sample data in the browser).
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  ...(mode === 'demo' ? { base: './', define: { 'import.meta.env.VITE_DEMO': '"1"' }, build: { outDir: '../docs/demo', emptyOutDir: true } } : {}),
  server: { port: 5173 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    css: false,
  },
}))
