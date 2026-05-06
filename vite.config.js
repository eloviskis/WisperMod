import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    // Proxy apenas em dev local — em produção usa VITE_API_URL
    proxy: {
      '/upload':   'http://localhost:8000',
      '/download': 'http://localhost:8000',
      '/ws':       { target: 'ws://localhost:8000', ws: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
