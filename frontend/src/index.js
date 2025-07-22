import React from 'react';
import ReactDOM from 'react-dom/client';
import './styles/index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import { AuthProvider } from './features/auth/components/context/AuthContext';
import AuthGate from './features/auth/components/context/AuthGate';

// ⚡ Aplica el tema antes de renderizar
const preferredTheme = localStorage.getItem('preferred-theme') || 'system';
if (preferredTheme === 'system') {
  const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  document.documentElement.setAttribute('data-theme', systemPrefersDark ? 'dark' : 'light');
} else {
  document.documentElement.setAttribute('data-theme', preferredTheme);
}


const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <AuthProvider>
      <AuthGate>
        <App />
      </AuthGate>
    </AuthProvider>
  </React.StrictMode>
);

reportWebVitals();
