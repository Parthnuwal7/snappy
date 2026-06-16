import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// Tauri (desktop) needs a relative asset base; the web build (Vercel) needs an
// absolute base so assets resolve on deep routes such as
// /i/:userId/:invoiceId/:sig. With a relative base the browser would request
// them from /i/1/829/assets/… which the SPA rewrite answers with index.html
// (wrong MIME) → the bundle fails to load and the page renders blank.
// Tauri sets TAURI_ENV_PLATFORM (v2) / TAURI_PLATFORM (v1) during its build.
const isTauri = !!(process.env.TAURI_ENV_PLATFORM || process.env.TAURI_PLATFORM)

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
  },
  // Absolute for web (deep routes), relative for Tauri. See isTauri note above.
  base: isTauri ? './' : '/',
  // Build configuration for Tauri
  build: {
    outDir: 'dist',
    target: 'esnext',
    minify: 'oxc',
  },
})
