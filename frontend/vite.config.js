import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1600,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('plotly.js-cartesian-dist-min') || id.includes('react-plotly.js')) {
            return 'plotly-vendor'
          }
          if (id.includes('jspdf') || id.includes('html2canvas') || id.includes('purify')) {
            return 'jspdf-vendor'
          }
          if (id.includes('wavesurfer.js')) {
            return 'wavesurfer-vendor'
          }
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
