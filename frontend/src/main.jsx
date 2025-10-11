import App from './App';
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from '@/features/auth/components/context/AuthContext';
import './styles/index.css';

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
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
          <App />
        </BrowserRouter>
      </AuthProvider>
  </QueryClientProvider>
  </React.StrictMode>
);

