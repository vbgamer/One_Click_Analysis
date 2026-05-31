import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/auth':      { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/users':     { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/admin':     { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/credits':   { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/status':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/reports':   { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/upload':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/my-reports':{ target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/static':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health':    { target: 'http://127.0.0.1:8000', changeOrigin: true },

      // ── AI Intelligence endpoints ──────────────────────────────────────────
      '/analyze':   { target: 'http://127.0.0.1:8000', changeOrigin: true },

      // ── WebSocket (AI chat) ────────────────────────────────────────────────
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        changeOrigin: true,
      },
    }
  }
})
