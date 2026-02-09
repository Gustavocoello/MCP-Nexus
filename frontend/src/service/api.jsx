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
    let token = null;

    // 1. Intentar obtener el token de Clerk (Plan A)
    if (typeof getTokenFunction === 'function') { 
      try {
        token = await getTokenFunction({ template: 'backend-api-jarvis' });
      } catch (error) {
        apiLogger.error('[api.js] Error obteniendo token de Clerk:', error);
      }
    }

    // 2. Si Clerk no está listo, buscar en LocalStorage (Plan B - Paracaídas)
    if (!token) {
      token = localStorage.getItem('jarvis_token');
      if (token) {
        apiLogger.info('[api.js] Usando token de respaldo (LocalStorage)');
      }
    }

    // 3. Inyectar el token si existe
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      apiLogger.warn('[api.js] No se encontró token en ninguna fuente');
    }

    return config;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
