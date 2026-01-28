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
  'http://127.0.0.1:5000'

const VITE_HOST = process.env.FRONTEND_HOST || process.env.VITE_HOST || '0.0.0.0'
const VITE_PORT_RAW = process.env.FRONTEND_PORT || process.env.VITE_PORT || '3001'
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
      },
    },
  },
  preview: {
    host: VITE_HOST,
    port: VITE_PORT,
    strictPort: STRICT_PORT,
  },
});
