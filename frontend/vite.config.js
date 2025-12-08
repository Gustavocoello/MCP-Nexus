import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    open: true
  },
  // Optimización de dependencias
  optimizeDeps: {
    include: [
      "@modelcontextprotocol/sdk/client",
      "@modelcontextprotocol/sdk/client/streamableHttp"
    ]
  },
  // Configuración de build (solo una vez)
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks: {
          'clerk': ['@clerk/clerk-react'],
          'vendor': ['react', 'react-dom', 'react-router-dom'],
        }
      }
    }
  }
})