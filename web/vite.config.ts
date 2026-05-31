import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// In dev we run Vite (HMR) and proxy API/WS calls to the FastAPI backend, so the
// app always talks to same-origin relative URLs (/api, /ws) — which also works
// in production where FastAPI serves the built files.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/ws': { target: 'http://localhost:8000', ws: true },
      '/health': 'http://localhost:8000',
    },
  },
})
