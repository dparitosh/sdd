import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory
  const repoRoot = resolve(__dirname, '..')
  const env = loadEnv(mode, repoRoot, '')
  const API_BASE_URL = env.API_BASE_URL || env.VITE_API_BASE_URL || env.VITE_API_URL || 'http://127.0.0.1:5000'
  const HOST = env.FRONTEND_HOST || env.VITE_HOST || '0.0.0.0'
  const PORT_RAW = env.FRONTEND_PORT || env.VITE_PORT || '3001'
  const STRICT_PORT = (env.VITE_STRICT_PORT || env.STRICT_PORT || '').toLowerCase() === 'true'

  const VITE_PORT = parseInt(PORT_RAW, 10)
  if (Number.isNaN(VITE_PORT)) {
    throw new Error(`Invalid FRONTEND_PORT/VITE_PORT value: ${PORT_RAW}`)
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': resolve(__dirname, './src'),
        '@ui': resolve(__dirname, './src/components/ui'),
      },
    },
    server: {
      host: HOST,
      port: VITE_PORT,
      strictPort: STRICT_PORT,
      proxy: {
        '/api': {
          target: API_BASE_URL,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host: HOST,
      port: VITE_PORT,
      strictPort: STRICT_PORT,
    },
  }
})
