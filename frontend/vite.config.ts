import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'
import tailwindcss from '@tailwindcss/vite'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory
  const repoRoot = resolve(__dirname, '..')
  const env = loadEnv(mode, repoRoot, '')

  const HOST = env.FRONTEND_HOST || env.VITE_HOST
  const PORT_RAW = env.FRONTEND_PORT || env.VITE_PORT
  const STRICT_PORT = (env.VITE_STRICT_PORT || env.STRICT_PORT || '').toLowerCase() === 'true'

  if (!HOST) {
    throw new Error('Missing FRONTEND_HOST (or VITE_HOST). Set it in your .env.')
  }
  if (!PORT_RAW) {
    throw new Error('Missing FRONTEND_PORT (or VITE_PORT). Set it in your .env.')
  }

  const API_BASE_URL =
    env.API_BASE_URL ||
    env.VITE_API_BASE_URL ||
    env.VITE_API_URL ||
    (env.BACKEND_HOST && env.BACKEND_PORT ? `http://${env.BACKEND_HOST}:${env.BACKEND_PORT}` : undefined)

  if (!API_BASE_URL) {
    throw new Error(
      'Missing backend API URL configuration. Set API_BASE_URL (recommended) or set BACKEND_HOST and BACKEND_PORT in your .env.'
    )
  }

  const VITE_PORT = parseInt(PORT_RAW, 10)
  if (Number.isNaN(VITE_PORT)) {
    throw new Error(`Invalid FRONTEND_PORT/VITE_PORT value: ${PORT_RAW}`)
  }

  return {
    plugins: [react(), tailwindcss()],
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
          proxyTimeout: 180_000, // 3 min — allows LLM responses (Ollama can take ~120 s)
          timeout: 180_000,
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
