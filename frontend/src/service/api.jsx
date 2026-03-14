// src/service/api.jsx
import axios from 'axios';
import { apiLogger } from '@/components/controller/log/logger.jsx';

// 1. La Fábrica (Para el futuro SDK)
export const createChatClient = ({ baseURL, getToken }) => {
  const instance = axios.create({
    baseURL: baseURL || import.meta.env.VITE_URL,
    headers: { 'Content-Type': 'application/json' },
    withCredentials: true,
  });

  instance.interceptors.request.use(async (config) => {
    let token = null;
    if (typeof getToken === 'function') {
      token = await getToken();
    }
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  return instance;
};

// 2. LA SOLUCIÓN AL ERROR:
// Creamos una variable interna para guardar la función que Clerk nos dará
let globalGetToken = null;

// Re-exportamos setAuthToken para que App.jsx no explote, 
// pero ahora solo guarda la referencia a la función.
export const setAuthToken = (getTokenFn) => {
  globalGetToken = getTokenFn;
};

// 3. Exportamos la instancia por defecto que usa esa variable interna
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

apiClient.interceptors.request.use(async (config) => {
  if (globalGetToken) {
    try {
      // Aquí es donde Clerk hace su magia
      const token = await globalGetToken({ template: 'backend-api-jarvis' });
      if (token) config.headers.Authorization = `Bearer ${token}`;
    } catch (e) {
      apiLogger.error("Error obteniendo token en interceptor", e);
    }
  }
  return config;
});

export default apiClient;