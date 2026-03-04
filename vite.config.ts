import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";
import { config } from 'dotenv';
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

// Load environment variables
config();

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const projectRoot = process.env.PROJECT_ROOT || __dirname
// Support both current and legacy naming conventions.
// Canonical names are used across the Windows scripts:
//   - FRONTEND_HOST / FRONTEND_PORT
//   - API_BASE_URL
// Legacy names (still accepted): VITE_HOST, VITE_PORT, VITE_API_URL, VITE_API_BASE_URL
const API_BASE_URL =
  process.env.API_BASE_URL ||
  process.env.VITE_API_BASE_URL ||
  // older deployment scripts
  process.env.VITE_API_URL ||
  (process.env.BACKEND_HOST && process.env.BACKEND_PORT
    ? `http://${process.env.BACKEND_HOST}:${process.env.BACKEND_PORT}`
    : undefined)

if (!API_BASE_URL) {
  throw new Error(
    'Missing backend API URL configuration. Set API_BASE_URL (recommended) or set BACKEND_HOST and BACKEND_PORT in your .env.'
  )
}

const VITE_HOST = process.env.FRONTEND_HOST || process.env.VITE_HOST
const VITE_PORT_RAW = process.env.FRONTEND_PORT || process.env.VITE_PORT

if (!VITE_HOST) {
  throw new Error('Missing FRONTEND_HOST (or VITE_HOST). Set it in your .env.')
}
if (!VITE_PORT_RAW) {
  throw new Error('Missing FRONTEND_PORT (or VITE_PORT). Set it in your .env.')
}
const VITE_PORT = parseInt(VITE_PORT_RAW, 10)
if (Number.isNaN(VITE_PORT)) {
  throw new Error(`Invalid FRONTEND_PORT/VITE_PORT value: ${VITE_PORT_RAW}`)
}

// Default to non-strict ports in dev (Vite will auto-pick the next free port).
// Set VITE_STRICT_PORT=true to force a hard failure on port conflicts.
const STRICT_PORT = (process.env.VITE_STRICT_PORT || process.env.STRICT_PORT || '').toLowerCase() === 'true'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': resolve(projectRoot, 'frontend/src'),
      '@ui': resolve(projectRoot, 'frontend/src/components/ui'),
    }
  },
  root: './frontend',
  server: {
    host: VITE_HOST,
    port: VITE_PORT,
    strictPort: STRICT_PORT,
    proxy: {
      '/api': {
        target: API_BASE_URL,
        changeOrigin: true,
        secure: false,
        proxyTimeout: 180_000,  // 3 min — allows LLM responses (Ollama/OpenAI can take ~120 s)
        timeout: 180_000,
      },
    },
  },
  preview: {
    host: VITE_HOST,
    port: VITE_PORT,
    strictPort: STRICT_PORT,
  },
});
