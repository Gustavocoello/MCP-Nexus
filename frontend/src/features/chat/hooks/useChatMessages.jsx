// features/chat/hooks/useChatMessages.js
import { useEffect, useRef, useCallback, useMemo } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { fetchChatMessages } from '../utils/chatApi';
import { parseChatMessagesResponse } from '../utils/chatResponseParser';
import { appendMessageToCache, prependMessagesToCache, trimChatCache } from '../utils/chatCacheHelpers';
import chatMemoryCache from '../utils/chatMemoryCache';
import Logger from '@/components/controller/log/logger';

const log = new Logger('useChatMessages');

export default function useChatMessages(chatId, options = {}) {
  const {
    limit = 10,
    keep = 10,
    maxChats = 5,
    enabled = true,
    offlineMode = true
  } = options;

  const queryClient = useQueryClient();
  const prevChatRef = useRef(null);

  const query = useInfiniteQuery({
    queryKey: ['chatMessages', chatId],
    queryFn: async ({ pageParam = null }) => {
      if (!chatId) return { messages: [], hasMore: false };

      // Intento de lectura de RAM
      if ((offlineMode && !pageParam) || (!pageParam && chatMemoryCache.get(chatId))) {
        const cached = chatMemoryCache.get(chatId);
        if (cached) {
          log.info(`[RAM] Cargando ${cached.length} mensajes para el chat: ${chatId}`);
          return { messages: cached, hasMore: false };
        }
      }

      log.info(`[API] Solicitando mensajes al backend/Redis para el chat: ${chatId}`);
      const rawData = await fetchChatMessages(chatId, limit, pageParam);
      return parseChatMessagesResponse(rawData, limit);
    },
    getNextPageParam: (lastPage) =>
      lastPage.hasMore ? lastPage.messages[lastPage.messages.length - 1]?.id : undefined,
    enabled: enabled && !!chatId,
    staleTime: Infinity,
    gcTime: 1000 * 60 * 5, // Cambio: gcTime en vez de cacheTime (nueva API)
  });

  const flatMessages = useMemo(
    () => query.data ? query.data.pages.flatMap(p => p.messages) : [],
    [query.data]
  );

  const lastUserMessageId = useMemo(() => {
    const userMsgs = flatMessages.filter(m => m.role === 'user');
    return userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].id : null;
  }, [flatMessages]);

  // GESTIÓN DE RAM
  // ============================================================
  useEffect(() => {
    if (chatId && flatMessages.length) {
      const isStreaming = flatMessages.some(m => m.stable === false);
      if (isStreaming) {
        log.debug(`[RAM] Skipping save - mensaje en streaming`);
        return;
      }

      const lastMsgs = flatMessages.slice(-keep);
      chatMemoryCache.set(chatId, lastMsgs);
      log.info(
        `[RAM] Snapshot: ${lastMsgs.length} guardados / ${flatMessages.length} totales en pantalla`
      );

      const allCachedChats = chatMemoryCache.keys();
      if (allCachedChats.length > maxChats) {
        const oldestChat = allCachedChats[0];
        chatMemoryCache.delete(oldestChat);
        log.warn(`[RAM] Eliminando chat antiguo: ${oldestChat}`);
      }
    }
  }, [chatId, flatMessages, keep, maxChats]);

  // Limpiar cache de React Query al cambiar de chat
  useEffect(() => {
    const prev = prevChatRef.current;
    if (prev && prev !== chatId) {
      queryClient.removeQueries({ queryKey: ['chatMessages', prev] });
      log.debug(`[QueryClient] Limpiando caché de React Query para chat previo: ${prev}`);
    }
    prevChatRef.current = chatId;
  }, [chatId, queryClient]);

  const patchMessageInCache = useCallback((messageId, updater) => {
    log.info(`[PATCH] Actualizando mensaje: ${messageId}`);
    
    queryClient.setQueryData(['chatMessages', chatId], old => {
      if (!old) {
        log.warn('[PATCH] No hay datos en cache para actualizar');
        return old;
      }
      
      const newData = {
        ...old,
        pages: old.pages.map(page => ({
          ...page,
          messages: page.messages.map(msg => {
            if (msg.id === messageId) {
              const updated = typeof updater === 'function' ? updater(msg) : updater;
              log.debug(`[PATCH] Mensaje actualizado:`, { old: msg, new: updated });
              return { ...msg, ...updated };
            }
            return msg;
          })
        }))
      };
      
      return newData;
    });
  }, [queryClient, chatId]);

  const appendMessages = useCallback((msgs) => {
    log.info(`[APPEND] Añadiendo ${msgs.length} mensajes nuevos`);
    appendMessageToCache(queryClient, chatId, msgs);
    trimChatCache(queryClient, chatId, keep);
  }, [queryClient, chatId, keep]);

  return {
    ...query,
    messages: flatMessages,
    lastUserMessageId,
    isSuccess: query.isSuccess, 
    appendMessageToCache: appendMessages,
    updateMessageInCache: patchMessageInCache,
  };
}