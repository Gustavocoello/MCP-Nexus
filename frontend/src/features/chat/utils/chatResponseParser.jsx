// features/chat/utils/chatResponseParser.js

/**
 * Normaliza la respuesta del backend de mensajes de chat
 */
export const parseChatMessagesResponse = (data, limit) => {
  let messages = [];
  let hasMore = false;

  if (Array.isArray(data)) {
    messages = data;
    hasMore = data.length === limit;
  } else if (data.messages) {
    messages = data.messages;
    hasMore = Boolean(data.hasMore ?? data.has_more ?? (messages.length === limit));
  } else if (data.result?.messages) {
    messages = data.result.messages;
    hasMore = Boolean(
      data.result.hasMore ?? data.result.has_more ?? (messages.length === limit)
    );
  }

  return { messages, hasMore };
};
