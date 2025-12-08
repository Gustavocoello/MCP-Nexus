// src//service/api_service.js
import axios from 'axios';
import { apiLogger } from '@/components/controller/log/logger.jsx';
//import apiClient from './api'; // Tu instancia configurada de axios

//const REACT_APP = process.env.REACT_APP_URL; Localhost:5000 o la URL de tu backend en producción
//const REACT_APP_URL = process.env.REACT_APP_URL_AZURE_PROMPT; // Azure Functions Nube
// Vite
const VITE_APP = import.meta.env.VITE_URL;

// Función global para obtener el token
let getTokenFunction = null;

export const setAuthToken = (getTokenFn) => {
  getTokenFunction = getTokenFn;
};

// Helper para obtener headers con token
const getAuthHeaders = async (additionalHeaders = {}) => {
  const headers = { ...additionalHeaders };
  
  if (getTokenFunction) {
    try {
      const token = await getTokenFunction({ template: 'backend-api-jarvis' });
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (error) {
      apiLogger.error('Error obteniendo token:', error);
    }
  }
  
  return headers;
};



export const sendAnonymousMessage = async (promptText) => {
    try {
      const response = await axios.post(`${VITE_APP}/api/search/prompt`, {
        prompt: promptText
      },{
        headers: {
          'Content-Type': 'application/json; charset=utf-8"',
        }
      });
      return response.data; 
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Error al introducir el prompt');
    }
  };
   

// ========== Enviar mensaje con streaming (requiere auth) ==========
export const sendMessage = async ({chatId, text, hidden_context = '', tool = ''}, onPartialResponse = null, signal) => {
  try {
    // Verificamos si la señal ya fue abortada antes de iniciar la petición
    if (signal?.aborted) {
      throw new DOMException('Operation aborted by the user', 'AbortError');
    }
    // Obtener headers con token
    const headers = await getAuthHeaders({
      'Content-Type': 'application/json'
    });

const response = await fetch(`${VITE_APP}/api/chat/${chatId}/message`, {
  method: 'POST',
  headers,
  credentials: 'include',
  body: JSON.stringify({ text, hidden_context, tool }),
  signal, // Pasamos el signal al fetch para que pueda ser abortado
});

if (!response.ok || !response.body) {
  throw new Error("No se pudo conectar al servidor");
}

const reader = response.body.getReader();
const decoder = new TextDecoder();
let fullText = '';
let isAborted = false;

// Configuramos el manejador del aborto
const onAbort = () => {
  isAborted = true;
  reader.cancel('Operación cancelada por el usuario').catch(() =>{});
};

signal?.addEventListener('abort', onAbort);

try {
  while (!isAborted) {
    const { value, done } = await reader.read();
    
    // Verificamos si fue abortado durante la espera
    if (signal?.aborted) {
      throw new DOMException('Operation aborted by the user', 'AbortError');
    }

    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    fullText += chunk;

    if (onPartialResponse) onPartialResponse(fullText);
  }

  return fullText;
} finally {
  // Limpiamos el event listener
  signal?.removeEventListener('abort', onAbort);
  
  // Cerramos el reader si no está cerrado
  if (!isAborted) {
    await reader.cancel();
  }
}

  } catch (error) {
    // Distinguimos entre errores de aborto y otros errores
    if (error.name === 'AbortError') {
      apiLogger.info('Request aborted by user');
      throw error; // Relanzamos para manejo específico en el componente
    }
throw new Error(`Error sending message: ${error.message}`);

  }
};
// ========== Extraer contenido de archivos (requiere auth) ==========
export const extractFileContent = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  // Obtener headers con token
  const authHeaders = await getAuthHeaders({});

  const response = await fetch(`${VITE_APP}/api/chat/extract_file`, {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders,
    body: formData,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || 'Error al extraer archivo');
  }

  return data;
};