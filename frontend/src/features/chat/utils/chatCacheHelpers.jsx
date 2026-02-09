/**
 * features/chat/utils/chatCacheHelpers.jsx
 * Chat Cache Helpers - Funciones para manipular QueryClient cache
 */

import chatMemoryCache from './chatMemoryCache';
import Logger from '../../../components/controller/log/logger';

const log = new Logger('chatCacheHelpers');

/**
 * Añade uno o múltiples mensajes al final de la cache
 * @param {QueryClient} queryClient - Instance of QueryClient
 * @param {string} chatId - ID del chat
 * @param {Object|Array} newMessages - Mensaje(s) a agregar
 */
export const appendMessageToCache = (queryClient, chatId, newMessages) => {
  // VALIDACIONES
  if (!queryClient) {
    log.error('queryClient es requerido');
    return;
  }

  if (!chatId) {
    log.error('chatId es requerido');
    return;
  }

  // ⭐ CONVERTIR A ARRAY si es un solo mensaje
  const messagesArray = Array.isArray(newMessages) ? newMessages : [newMessages];

  // Validar que haya mensajes válidos
  const validMessages = messagesArray.filter(m => m && m.id);
  
  if (validMessages.length === 0) {
    log.error('❌ No hay mensajes válidos para agregar');
    return;
  }

  try {
    queryClient.setQueryData(['chatMessages', chatId], (old) => {
      // Si no hay cache previa, crear nueva
      if (!old || !old.pages) {
        log.info(`✨ Creando nueva cache para chat ${chatId}`);
        return {
          pages: [{ messages: validMessages, hasMore: false }],
          pageParams: [null]
        };
      }

      // Agregar mensajes a la primera página (más reciente)
      const firstPage = old.pages[0];
      const existingMessages = firstPage?.messages || [];
      
      // Filtrar duplicados
      const newUniqueMessages = validMessages.filter(
        newMsg => !existingMessages.some(existing => existing.id === newMsg.id)
      );

      if (newUniqueMessages.length === 0) {
        log.warn('⚠️ Todos los mensajes ya existen en cache');
        return old;
      }

      const updatedFirstPage = {
        ...firstPage,
        messages: [...existingMessages, ...newUniqueMessages]
      };

      const newPages = [updatedFirstPage, ...old.pages.slice(1)];

      log.info(
        `✅ ${newUniqueMessages.length} mensaje(s) agregado(s) a cache de chat ${chatId}`
      );

      return { ...old, pages: newPages };
    });

    // SINCRONIZAR con chatMemoryCache local
    const updatedCache = queryClient.getQueryData(['chatMessages', chatId]);
    if (updatedCache?.pages?.[0]?.messages) {
      const allMessages = updatedCache.pages.flatMap(p => p.messages || []);
      chatMemoryCache.set(chatId, allMessages);
    }

  } catch (error) {
    log.error('❌ Error en appendMessageToCache:', error);
  }
};

/**
 * Inserta mensajes más antiguos al inicio (para infinite scroll)
 * @param {QueryClient} queryClient
 * @param {string} chatId
 * @param {Array} olderMessages - Mensajes antiguos a insertar
 */
export const prependMessagesToCache = (queryClient, chatId, olderMessages = []) => {
  if (!queryClient) {
    log.error('queryClient es requerido');
    return;
  }

  if (!chatId) {
    log.error('chatId es requerido');
    return;
  }

  if (!Array.isArray(olderMessages)) {
    log.error('olderMessages debe ser un array');
    return;
  }

  if (olderMessages.length === 0) {
    log.warn('olderMessages está vacío, nada que agregar');
    return;
  }

  const validMessages = olderMessages.filter(m => m && m.id);
  if (validMessages.length === 0) {
    log.error('No hay mensajes válidos en olderMessages');
    return;
  }

  try {
    queryClient.setQueryData(['chatMessages', chatId], (old) => {
      if (!old || !old.pages) {
        log.info(`Creando nueva cache con mensajes antiguos para chat ${chatId}`);
        return {
          pages: [{ messages: validMessages, hasMore: true }],
          pageParams: [null]
        };
      }

      // Agregar nueva página al final (mensajes antiguos)
      const newPage = {
        messages: validMessages,
        hasMore: validMessages.length > 0
      };

      const newPages = [...old.pages, newPage];

      log.info(
        `${validMessages.length} mensajes antiguos agregados a cache de chat ${chatId}`
      );

      return { ...old, pages: newPages };
    });

  } catch (error) {
    log.error('Error en prependMessagesToCache:', error);
  }
};

/**
 * Recorta la caché para mantener solo los últimos N mensajes
 * @param {QueryClient} queryClient
 * @param {string} chatId
 * @param {number} keep - Número de mensajes a mantener (default: 10)
 */
export const trimChatCache = (queryClient, chatId, keep = 10) => {
  if (!queryClient || !chatId) {
    log.error('queryClient y chatId son requeridos');
    return;
  }

  if (keep < 1) {
    log.error('keep debe ser mayor a 0');
    return;
  }

  try {
    const key = ['chatMessages', chatId];
    const old = queryClient.getQueryData(key);

    if (!old || !old.pages || old.pages.length === 0) {
      log.debug(`No hay cache para recortar en chat ${chatId}`);
      return;
    }

    // Aplanar todas las páginas
    const flat = old.pages.flatMap(p => p.messages || []);

    if (flat.length <= keep) {
      log.debug(
        `Cache de chat ${chatId} tiene ${flat.length} mensajes, no necesita recorte (keep: ${keep})`
      );
      return;
    }

    // Mantener solo los últimos N mensajes
    const newest = flat.slice(-keep);

    // Determinar si había más mensajes antes
    const hadMore = flat.length > keep || old.pages.some(p => p.hasMore);

    // Reemplazar cache con una sola página
    queryClient.setQueryData(key, {
      pages: [{ messages: newest, hasMore: hadMore }],
      pageParams: [null]
    });

    log.info(
      `✂️ Cache recortada: ${flat.length} → ${newest.length} mensajes`
    );

    // SINCRONIZAR con chatMemoryCache
    chatMemoryCache.set(chatId, newest);

  } catch (error) {
    log.error('Error en trimChatCache:', error);
  }
};

/**
 * Invalida y limpia completamente la cache de un chat
 */
export const invalidateChatCache = (queryClient, chatId) => {
  if (!queryClient || !chatId) {
    log.error('queryClient y chatId son requeridos');
    return;
  }

  try {
    queryClient.removeQueries(['chatMessages', chatId]);
    chatMemoryCache.delete(chatId);
    log.info(`🗑️ Cache eliminada para chat ${chatId}`);
  } catch (error) {
    log.error('Error en invalidateChatCache:', error);
  }
};

/**
 * Reemplaza completamente la cache de un chat
 */
export const replaceChatCache = (queryClient, chatId, messages, hasMore = false) => {
  if (!queryClient || !chatId) {
    log.error('queryClient y chatId son requeridos');
    return;
  }

  if (!Array.isArray(messages)) {
    log.error('messages debe ser un array');
    return;
  }

  try {
    queryClient.setQueryData(['chatMessages', chatId], {
      pages: [{ messages, hasMore }],
      pageParams: [null]
    });

    chatMemoryCache.set(chatId, messages);

    log.info(
      `🔄 Cache reemplazada para chat ${chatId}: ${messages.length} mensajes`
    );
  } catch (error) {
    log.error('Error en replaceChatCache:', error);
  }
};

/**
 * Obtiene todos los mensajes de un chat desde cache
 */
export const getChatMessagesFromCache = (queryClient, chatId) => {
  if (!queryClient || !chatId) {
    return [];
  }

  try {
    const data = queryClient.getQueryData(['chatMessages', chatId]);
    if (!data?.pages) {
      return [];
    }

    return data.pages.flatMap(p => p.messages || []);
  } catch (error) {
    log.error('Error obteniendo mensajes de cache:', error);
    return [];
  }
};