import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    noDiscovery: true,
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    fs: {
      strict: false,
    },
    proxy: {
      '/ask-voice': 'http://127.0.0.1:8000',
      '/ask-text': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/stats': 'http://127.0.0.1:8000',
      '/chunking': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
    }
  },
  preview: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/ask-voice': 'http://127.0.0.1:8000',
      '/ask-text': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
      '/stats': 'http://127.0.0.1:8000',
      '/chunking': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
    }
  }
})
