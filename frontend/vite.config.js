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
  build: {
    outDir: "dist"
  },
  server: {
    open: true
  },
  // Para resolver las importaciones del SDK
  optimizeDeps: {
    include: [
      "@modelcontextprotocol/sdk/client",
      "@modelcontextprotocol/sdk/client/streamableHttp"
    ]
  }
})

