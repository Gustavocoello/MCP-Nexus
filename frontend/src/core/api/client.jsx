// src/sdk/core/client.jsx
import axios from 'axios';

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
let isInitialized = false; 
let currentAppId = 'project-portafolio'

// Re-exportamos setAuthToken para que App.jsx no explote, 
// pero ahora solo guarda la referencia a la función.
export const setAuthToken = (getTokenFn, appId) => {
  globalGetToken = getTokenFn;
  if (appId) currentAppId = appId;
  isInitialized = true; 
};

export const isApiReady = () => isInitialized; //

// 3. Exportamos la instancia por defecto que usa esa variable interna
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

apiClient.interceptors.request.use(async (config) => {
  //0. Inyectamos el ID del proyecto para la base de datos
  config.headers['X-Project-Origin'] = currentAppId;
  // 1. Intentamos sacar el token del LocalStorage (que tu hook ya guardó)
  let token = localStorage.getItem('jarvis_token');

  // 2. Si no está en LocalStorage, intentamos pedírselo a Clerk (globalGetToken)
  if (!token && globalGetToken) {
    try {
      token = await globalGetToken({ template: 'backend-api-jarvis' });
    } catch (e) {
      console.error("Error crítico recuperando token:", e);
    }
  }

  // 3. Si finalmente tenemos token, lo inyectamos
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  } else {
    // Si llegamos aquí sin token, abortamos la petición antes de que llegue al servidor
    // Esto evita el 401 y nos da tiempo a reintentar
    const controller = new AbortController();
    config.signal = controller.signal;
    controller.abort("Token no disponible aún");
  }

  return config;
}, (error) => Promise.reject(error));

export default apiClient;