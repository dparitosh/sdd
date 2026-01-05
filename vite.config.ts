import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig } from "vite";
import { config } from 'dotenv';
import { resolve } from 'path'

// Load environment variables
config();

const projectRoot = process.env.PROJECT_ROOT || import.meta.dirname
const API_BASE_URL = process.env.API_BASE_URL || process.env.VITE_API_BASE_URL
const VITE_HOST = process.env.FRONTEND_HOST || process.env.VITE_HOST
const VITE_PORT_RAW = process.env.FRONTEND_PORT || process.env.VITE_PORT

if (!API_BASE_URL) {
  throw new Error('Missing API_BASE_URL in environment (.env).');
}
if (!VITE_HOST) {
  throw new Error('Missing FRONTEND_HOST (or VITE_HOST) in environment (.env).');
}
if (!VITE_PORT_RAW) {
  throw new Error('Missing FRONTEND_PORT (or VITE_PORT) in environment (.env).');
}
const VITE_PORT = parseInt(VITE_PORT_RAW, 10)
if (Number.isNaN(VITE_PORT)) {
  throw new Error(`Invalid FRONTEND_PORT/VITE_PORT value: ${VITE_PORT_RAW}`)
}

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
    strictPort: true,
    proxy: {
      '/api': {
        target: API_BASE_URL,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
