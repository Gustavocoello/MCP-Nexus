import axios from 'axios';
//import apiClient from './api'; // Tu instancia configurada de axios

const REACT_APP = process.env.REACT_APP_URL; // Localhost:5000 o la URL de tu backend en producción
//const REACT_APP_URL = process.env.REACT_APP_URL_AZURE_PROMPT; // Azure Functions Nube


const onPrompt = async (promptText) => {
    try {
      const response = await axios.post(`${REACT_APP}/api/search/prompt`, { 
        prompt: promptText
      },{
        headers: {
          'Content-Type': 'application/json; charset=utf-8"',
        }
      });
      return response.data; // Asegúrate de que esto coincida con la estructura de tu backend
    } catch (error) {
      throw new Error(error.response?.data?.error || 'Error al introducir el prompt');
    }
  };
   
  export default onPrompt;


export const sendMessage = async (chatId, text, onPartialResponse = null, signal) => {
  try {
    // Verificamos si la señal ya fue abortada antes de iniciar la petición
    if (signal?.aborted) {
      throw new DOMException('Operation aborted by the user', 'AbortError');
    }

const response = await fetch(`${REACT_APP}/api/chat/${chatId}/message`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text }),
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
      console.log('Request aborted by user');
      throw error; // Relanzamos para manejo específico en el componente
    }
throw new Error(`Error sending message: ${error.message}`);

  }
};