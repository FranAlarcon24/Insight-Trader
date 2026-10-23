import react from '@vitejs/plugin-react'
import process from 'node:process'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // La interfaz llama a la API Python del agente
    // (python -m insight_trader.agent.server, puerto 8000 por defecto)
    proxy: {
      '/api': process.env.INSIGHT_API_URL ?? 'http://127.0.0.1:8000',
    },
  },
})
