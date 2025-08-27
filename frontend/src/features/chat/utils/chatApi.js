// features/chat/utils/chatApi.js
import apiClient from '../../../service/api';

/**
 * Obtiene mensajes paginados de un chat
 * @param {string} chatId 
 * @param {number} limit 
 * @param {string|null} before - ID del mensaje más antiguo para paginar
 */
export const fetchChatMessages = async (chatId, limit = 10, before = null) => {
  const params = { limit };
  if (before) params.before = before;

  const res = await apiClient.get(`/api/chat/${chatId}/messages`, {
    params,
    withCredentials: true,
  });

  return res.data;
};
