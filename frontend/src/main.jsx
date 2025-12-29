// frontend/src/main.jsx
import App from './App';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/features/auth/components/context/AuthContext';
import { injectSpeedInsights } from '@vercel/speed-insights';
import { ClerkProvider } from '@clerk/clerk-react'
import './styles/index.css';

// Obtener la clave pública de Clerk desde las variables de entorno
const PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

// Inicializar Vercel Speed Insights
if (import.meta.env.VITE_DEBUG === 'true') {
  injectSpeedInsights();
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

