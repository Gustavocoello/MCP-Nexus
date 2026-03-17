// src/services/api_service.js
import axios from 'axios';
import { apiLogger } from '@/components/controller/log/logger.jsx';
import apiClient from './api'; // Tu instancia de api.jsx

/**
 * Helper para manejar el streaming de forma agnóstica.
 * No depende de variables globales.
 */
export const sendMessage = async (
  { chatId, text, hidden_context = '', tool = '' }, 
  onPartialResponse = null, 
  signal,
  client = apiClient 
) => {
  try {
    if (signal?.aborted) throw new DOMException('Aborted', 'AbortError');
    let token = localStorage.getItem('jarvis_token');
    if (!token) {
      token = client.defaults.headers.common['Authorization']?.split(' ')[1];
    }
    const headers = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(`${client.defaults.baseURL}/api/chat/${chatId}/message`, {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({ text, hidden_context, tool }),
      signal,
    });

    if (response.status === 401) {
      throw new Error("No autorizado. Por favor, inicia sesión de nuevo.");
    }

    if (!response.ok || !response.body) {
      throw new Error("No se pudo conectar al servidor");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      fullText += chunk;

      if (onPartialResponse) onPartialResponse(fullText);
    }

    return fullText;

  } catch (error) {
    if (error.name === 'AbortError') {
      apiLogger.info('Streaming abortado por el usuario');
      throw error;
    }
    throw new Error(`Error en streaming: ${error.message}`);
  }
};

// Mensaje Anónimo
export const sendAnonymousMessage = async (promptText, client = defaultApiClient) => {
  try {
    // Usamos el cliente inyectado en lugar de 'axios' global
    const response = await client.post(`/api/search/prompt`, {
      prompt: promptText
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Error en mensaje anónimo');
  }
};

// Extracción de archivos
export const extractFileContent = async (file, client = defaultApiClient) => {
  const formData = new FormData();
  formData.append('file', file);

  // El cliente ya tiene el token gracias a los interceptores
  const response = await fetch(`${client.defaults.baseURL}/api/chat/extract_file`, {
    method: 'POST',
    headers: {
        // No enviamos Content-Type para que el navegador ponga el boundary del FormData
        'Authorization': client.defaults.headers.Authorization 
    },
    body: formData,
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || 'Error al extraer archivo');
  }

  return await response.json();
};