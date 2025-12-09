import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory
  const env = loadEnv(mode, process.cwd(), '')
  const API_BASE_URL = env.API_BASE_URL || 'http://127.0.0.1:5000'
  const VITE_PORT = parseInt(env.VITE_PORT || '3001')

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
