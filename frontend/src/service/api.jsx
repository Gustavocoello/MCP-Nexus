// src/services/api.js
import axios from 'axios';
import { apiLogger } from '@/components/controller/log/logger.jsx';

//const REACT_APP = process.env.REACT_APP_URL; Esto viene del .env
const VITE_APP = import.meta.env.VITE_URL;


// Instancia de axios con configuración básica
const apiClient = axios.create({
  baseURL: VITE_APP,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});
// Función para establecer el método getToken globalmente
let getTokenFunction = null;

export const setAuthToken = (getTokenFn) => {
  getTokenFunction = getTokenFn;
};

// Interceptor para agregar el token JWT a cada request
apiClient.interceptors.request.use(
  async (config) => {
    // Solo agregar token si hay una función configurada
    if (getTokenFunction) {
      try {
        const token = await getTokenFunction({ template: 'backend-api-jarvis' });
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch (error) {
        apiLogger.error('[api.js] Error obteniendo token:', error);
      }
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor para manejar respuestas 401 (opcional pero útil)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      apiLogger.error('[api.js] No autorizado - Token inválido o expirado');
      // Aquí podrías redirigir al login si es necesario
    }
    return Promise.reject(error);
  }
);

export default apiClient;
