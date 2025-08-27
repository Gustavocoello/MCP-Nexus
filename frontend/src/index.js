import App from './App';
import React from 'react';
import ReactDOM from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import AuthGate from './features/auth/components/context/AuthGate';
import { AuthProvider } from './features/auth/components/context/AuthContext';
import './styles/index.css';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// ⚡ Aplica el tema antes de renderizar
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
      <AuthGate>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthGate>
    </AuthProvider>
  </QueryClientProvider>
  </React.StrictMode>
);

reportWebVitals();
