// src/services/chatService.js
import apiClient from './api';

// 1. Obtener todos los chats
export const getAllChats = async () => {
  try {
    const res = await apiClient.get('/api/chat');
    return res.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Error al obtener los chats');
  }
};

// 2. Obtener mensajes de un chat específico
export const getChatMessages = async (chatId) => {
  try {
    const res = await apiClient.get(`/api/chat/${chatId}/messages`);
    return res.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Error al obtener los mensajes');
  }
};

// 3. Crear un nuevo chat
export const createChat = async (newChat) => {
  try {
    const res = await apiClient.post('/api/chat', newChat);
    return res.data;
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Error al crear el chat');
  }
};

// 4. Enviar mensaje a un chat
export const sendMessage = async (chatId, text) => {
  try {
    const res = await apiClient.post(`/api/chat/${chatId}/message`, { text });
    return res.data; // { reply: "respuesta de IA" }
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Error al enviar el mensaje');
  }
};

// 5. Borrar un chat (opcional)
export const deleteChat = async (chatId) => {
  try {
    await apiClient.delete(`/api/chat/${chatId}`);
  } catch (error) {
    throw new Error(error.response?.data?.error || 'Error al borrar el chat');
  }
};