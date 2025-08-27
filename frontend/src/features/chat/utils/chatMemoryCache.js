// features/chat/utils/chatMemoryCache.js
const chatMemoryCache = {
  lastChatId: null,
  lastMessages: [],
  
  set(chatId, messages) {
    this.lastChatId = chatId;
    this.lastMessages = messages;
  },

  get(chatId) {
    if (this.lastChatId === chatId) {
      return this.lastMessages;
    }
    return null;
  }
};

export default chatMemoryCache;
