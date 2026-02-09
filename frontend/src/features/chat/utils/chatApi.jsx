// features/chat/utils/chatApi.js
import apiClient from '../../../service/api';

/**
 * Obtiene mensajes paginados de un chat
 * @param {string} chatId 
 */
export const fetchChatMessages = async (chatId, limit = 10, before = null) => {
  //const params = { limit };
  //if (before) params.before = before;

  const res = await apiClient.get(`/api/chat/${chatId}/messages/recent`, {
    //params,
    withCredentials: true,
  });

  return res.data;
};
