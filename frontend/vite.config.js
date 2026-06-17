import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      // APUNTA DIRECTAMENTE AL SRC DEL SDK, NO AL DIST
      "jarvis-sdk-ui": path.resolve(__dirname, "../sdk/jarvis-ui/src/index.jsx")
    },
    dedupe: ["react", "react-dom", "@tanstack/react-query"],
    preserveSymlinks: false,
  },
  server: {
    fs: {
      // Permitimos que Vite lea archivos fuera de la carpeta 'frontend'
      allow: ['..']
    },
     resolve: {
    // Si usas link de pnpm, a veces Vite necesita que respetes los symlinks
    preserveSymlinks: true 
    }
  },
  optimizeDeps: {
    // IMPORTANTE: Excluimos el SDK para que no intente pre-empaquetarlo
    exclude: ["jarvis-sdk-ui"], 
  }
});