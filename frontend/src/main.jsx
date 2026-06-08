// frontend/src/main.jsx

if (typeof global === 'undefined') {
  window.global = window;
}
if (typeof window.require === 'undefined') {
  window.require = (path) => {
    if (path === 'react') return React;
    if (path === 'react-dom') return ReactDOM;
    throw new Error(`Could not resolve require("${path}")`);
  };
}

import App from './App';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/core/auth/AuthContext';
import { injectSpeedInsights } from '@vercel/speed-insights';
import { ClerkProvider } from '@clerk/clerk-react'
import './styles/index.css';

// Obtener la clave pública de Clerk desde las variables de entorno
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

// Inicializar Vercel Speed Insights
// En main.jsx, cambia eso por:
if (import.meta.env.VITE_DEBUG === 'true' && !window.__INSIGHTS_INJECTED__) {
  injectSpeedInsights();
  window.__INSIGHTS_INJECTED__ = true;
}
// Aplica el tema antes de renderizar
const preferredTheme = localStorage.getItem('preferred-theme') || 'system';
if (preferredTheme === 'system') {
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.setAttribute('data-theme', systemPrefersDark ? 'dark' : 'light');
} else {
  document.documentElement.setAttribute('data-theme', preferredTheme);
}

const queryClient = new QueryClient();
const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <ClerkProvider
    publishableKey={PUBLISHABLE_KEY} 
    fallbackRedirectUrl="/"
  >
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
          <App />
        </BrowserRouter>
      </AuthProvider>
  </QueryClientProvider>
  </ClerkProvider>
  
);

