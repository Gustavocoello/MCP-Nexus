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
    if (typeof getTokenFunction === 'function') { 
      try {
        const token = await getTokenFunction({ template: 'backend-api-jarvis' });
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        } else {
          // Si no hay token, mejor no enviamos el header vacío o lanzamos aviso
          apiLogger.warn('[api.js] getToken devolvió null');
        }
      } catch (error) {
        apiLogger.error('[api.js] Error obteniendo token:', error);
      }
    } else {
      // Esto explica por qué el Sidebar dice "Authorization header missing"
      apiLogger.warn('[api.js] getTokenFunction no está lista todavía');
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
