import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react-swc";
import { defineConfig, PluginOption } from "vite";
import { config } from 'dotenv';
import createIconImportProxy from "@github/spark/vitePhosphorIconProxyPlugin";
import { resolve } from 'path'

// Load environment variables
config();

const projectRoot = process.env.PROJECT_ROOT || import.meta.dirname
const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:5000'
const VITE_PORT = parseInt(process.env.VITE_PORT || '3001')

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // DO NOT REMOVE
    createIconImportProxy() as PluginOption,
    // Temporarily disabled to test port issue
    // sparkPlugin() as PluginOption,
  ],
  resolve: {
    alias: {
      '@': resolve(projectRoot, 'frontend/src'),
      '@ui': resolve(projectRoot, 'frontend/src/components/ui'),
    }
  },
  root: './frontend',
  server: {
    host: '0.0.0.0', // Listen on all interfaces for Codespaces
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
