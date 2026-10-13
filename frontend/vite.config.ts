import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// The React app calls /api/*; in development Vite proxies that to the FastAPI backend.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.STYLEAI_BACKEND_URL || 'http://127.0.0.1:8000'
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: { '/api': { target: backend, changeOrigin: true } },
    },
    preview: {
      port: 4173,
      proxy: { '/api': { target: backend, changeOrigin: true } },
    },
    build: {
      chunkSizeWarningLimit: 1600,
      rollupOptions: {
        output: {
          manualChunks: (id) => (id.includes('node_modules/three') || id.includes('@react-three') ? 'three' : undefined),
        },
      },
    },
  }
})
