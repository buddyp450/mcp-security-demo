import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND_PORT = Number(process.env.BACKEND_PORT ?? 8001)
const FRONTEND_PORT = Number(process.env.FRONTEND_PORT ?? 5174)

export default defineConfig({
  plugins: [react()],
  server: {
    port: FRONTEND_PORT,
    proxy: {
      '/api': `http://localhost:${BACKEND_PORT}`,
      '/ws': {
        target: `ws://localhost:${BACKEND_PORT}`,
        ws: true
      }
    }
  }
})
