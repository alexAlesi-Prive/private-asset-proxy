import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies API calls to the Python engine service on :5530.
// In production the built SPA is served by that same service (same origin).
export default defineConfig({
  plugins: [react()],
  // Absolute base: the SPA is served at the site root by the engine service, so
  // asset URLs like /assets/prive-logo-xxx.png resolve on every route (and via
  // the SPA fallback), unlike relative './' which depends on the current path.
  base: '/',
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5530',
      '/healthz': 'http://localhost:5530',
    },
  },
  build: { outDir: 'dist' },
})
