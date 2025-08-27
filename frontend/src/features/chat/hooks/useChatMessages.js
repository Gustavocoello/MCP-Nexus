// features/chat/hooks/useChatMessages.js
import { useEffect, useRef, useCallback, useMemo } from 'react';
import { useInfiniteQuery, useQueryClient } from '@tanstack/react-query';
import { fetchChatMessages } from '../utils/chatApi';
import { parseChatMessagesResponse } from '../utils/chatResponseParser';
import { appendMessageToCache, prependMessagesToCache, trimChatCache } from '../utils/chatCacheHelpers';
import chatMemoryCache from '../utils/chatMemoryCache';


export default function useChatMessages(chatId, options = {}) {
  const {
    limit = 10,              // mensajes a pedir por página
    keep = 10,               // mensajes que guardaremos al cambiar chat
    enabled = true,
    offlineMode = true
  } = options;

  const queryClient = useQueryClient();
  const prevChatRef = useRef(null);
  //const lastChatCacheRef = useRef({ chatId: null, messages: [] });

  // Solo pedimos mensajes cuando es necesario
  const query = useInfiniteQuery({
    queryKey: ['chatMessages', chatId],
    queryFn: async ({ pageParam = null }) => {
      if (!chatId) return { messages: [], hasMore: false };

      // Si tenemos snapshot global, úsalo y no llames backend
      if ((offlineMode && !pageParam) || (!pageParam && chatMemoryCache.get(chatId))) {
        const cached = chatMemoryCache.get(chatId);
        if (cached) {
          return { messages: cached, hasMore: false }; // 👈 no pedimos más
        }
      }

      const rawData = await fetchChatMessages(chatId, limit, pageParam);
      return parseChatMessagesResponse(rawData, limit);
    },
    getNextPageParam: (lastPage) =>
      lastPage.hasMore
        ? lastPage.messages[lastPage.messages.length - 1]?.id
        : undefined,
    enabled: enabled && !!chatId,
    staleTime: 0,
    cacheTime: 0, // nunca cachear más allá del chat activo
  });

  const flatMessages = useMemo(
    () => query.data ? query.data.pages.flatMap(p => p.messages) : [],
    [query.data]
  );

  // Al cambiar de chat, guardamos snapshot y borramos cache anterior
  // 1. Guardar snapshot SIEMPRE del chat actual
useEffect(() => {
  if (chatId && flatMessages.length) {
    const lastMsgs = flatMessages.slice(-keep);
    chatMemoryCache.set(chatId, lastMsgs);
  }
}, [chatId, flatMessages, keep]);

// 2. Limpiar cache cuando CAMBIA de chat
useEffect(() => {
  const prev = prevChatRef.current;
  if (prev && prev !== chatId) {
    queryClient.removeQueries({ queryKey: ['chatMessages', prev] });
  }
  prevChatRef.current = chatId;
}, [chatId, queryClient]);


  const patchMessageInCache = useCallback((messageId, updater) => {
    queryClient.setQueryData(['chatMessages', chatId], old => {
      if (!old) return old;
      return {
        ...old,
        pages: old.pages.map(page => ({
          ...page,
          messages: page.messages.map(msg =>
            msg.id === messageId
              ? { ...msg, ...(typeof updater === 'function' ? updater(msg) : updater) }
              : msg
          )
        }))
      };
    });
  }, [queryClient, chatId]);

  return {
    ...query,
    messages: flatMessages,
    appendMessageToCache: (msgs) => appendMessageToCache(queryClient, chatId, msgs),
    prependMessagesToCache: (msgs) => prependMessagesToCache(queryClient, chatId, msgs),
    updateMessageInCache: patchMessageInCache,
    trimCache: () => trimChatCache(queryClient, chatId, keep),
  };
}
