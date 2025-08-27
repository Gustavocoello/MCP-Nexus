// features/chat/utils/chatCacheHelpers.js

/**
 * Añade un mensaje nuevo al final de la cache
 */
export const appendMessageToCache = (queryClient, chatId, newMessage) => {
  if (!chatId || !newMessage) return;
  queryClient.setQueryData(['chatMessages', chatId], (old) => {
    if (!old) {
      return { pages: [{ messages: [newMessage], hasMore: false }], pageParams: [] };
    }
    const newPages = old.pages.map((page, idx) =>
      idx === 0 ? { ...page, messages: [...page.messages, newMessage] } : page
    );
    return { ...old, pages: newPages };
  });
};

/**
 * Inserta mensajes más antiguos al inicio
 */
export const prependMessagesToCache = (queryClient, chatId, olderMessages = []) => {
  if (!chatId || !Array.isArray(olderMessages) || olderMessages.length === 0) return;
  queryClient.setQueryData(['chatMessages', chatId], (old) => {
    if (!old) {
      return { pages: [{ messages: olderMessages, hasMore: olderMessages.length > 0 }], pageParams: [] };
    }
    const newPages = [...old.pages, { messages: olderMessages, hasMore: false }];
    return { ...old, pages: newPages };
  });
};

/**
 * Recorta la caché de un chat para mantener solo los últimos `keep` mensajes.
 * - queryClient: instance of QueryClient
 * - chatId: id del chat a recortar
 * - keep: número de mensajes más nuevos a conservar
 *
 * Nota: asumimos que `old.pages` puede contener múltiples páginas y que
 * page 0 (o el flatten) incluye los mensajes más recientes.
 */
export const trimChatCache = (queryClient, chatId, keep = 10) => {
  if (!chatId) return;
  const key = ['chatMessages', chatId];
  const old = queryClient.getQueryData(key);

  if (!old || !old.pages) return;

  // Aplanamos todas las páginas en un solo array
  const flat = old.pages.flatMap(p => p.messages || []);
  if (flat.length <= keep) {
    // no hay nada que recortar
    return;
  }

  // Conservamos los últimos `keep` mensajes (más recientes al final)
  const newest = flat.slice(-keep);

  // Decidir si hay más mensajes (si antes tenía más de keep)
  const hadMore = flat.length > keep || old.pages.some(p => p.hasMore);

  // Reemplazamos la cache por una sola página que contiene los `keep` mensajes.
  queryClient.setQueryData(key, {
    pages: [{ messages: newest, hasMore: hadMore }],
    pageParams: [],
  });
};
