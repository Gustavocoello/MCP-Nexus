import { useState, useCallback } from 'react';

export const useChatState = () => {
  const [activeChatId, setActiveChatId] = useState(null);
  const [localMessages, setLocalMessages] = useState([]);
  const [hasSentMessage, setHasSentMessage] = useState(false);

  // Esta función es clave para tu Agente: permite resetear todo
  const resetChat = useCallback(() => {
    setActiveChatId(null);
    setLocalMessages([]);
    setHasSentMessage(false);
  }, []);

  return {
    activeChatId,
    setActiveChatId,
    localMessages,
    setLocalMessages,
    hasSentMessage,
    setHasSentMessage,
    resetChat
  };
};