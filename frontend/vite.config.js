import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // APUNTA DIRECTAMENTE AL SRC DEL SDK, NO AL DIST
      "jarvis-sdk-ui": path.resolve(__dirname, "../../jarvis-sdk/jarvis-ui/src/index.jsx"),
    },
    dedupe: ["react", "react-dom", "@tanstack/react-query"],
    preserveSymlinks: false,
  },
  server: {
    fs: {
      // Permitimos que Vite lea archivos fuera de la carpeta 'frontend'
      allow: ['..', '../../jarvis-sdk']
    }
  },
  optimizeDeps: {
    // IMPORTANTE: Excluimos el SDK para que no intente pre-empaquetarlo
    exclude: ["jarvis-sdk-ui"],
  }
});