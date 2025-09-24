import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
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

