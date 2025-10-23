import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

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
  // Tauri expects a relative base path
  base: './',
  // Build configuration for Tauri
  build: {
    outDir: 'dist',
    target: 'esnext',
    minify: 'esbuild',
  },
})
