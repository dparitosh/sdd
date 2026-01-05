import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory
  const repoRoot = path.resolve(__dirname, '..')
  const env = loadEnv(mode, repoRoot, '')
  const API_BASE_URL = env.API_BASE_URL || env.VITE_API_BASE_URL
  const PORT_RAW = env.FRONTEND_PORT || env.VITE_PORT

  if (!API_BASE_URL) {
    throw new Error('Missing API_BASE_URL (or VITE_API_BASE_URL) in environment (.env).')
  }
  if (!PORT_RAW) {
    throw new Error('Missing FRONTEND_PORT (or VITE_PORT) in environment (.env).')
  }

  const VITE_PORT = parseInt(PORT_RAW, 10)
  if (Number.isNaN(VITE_PORT)) {
    throw new Error(`Invalid FRONTEND_PORT/VITE_PORT value: ${PORT_RAW}`)
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: VITE_PORT,
      proxy: {
        '/api': {
          target: API_BASE_URL,
          changeOrigin: true,
        },
      },
    },
  }
})
