import { useState, useRef, useEffect } from 'react';
import { chatEvents } from '../utils/chatEvents';

export const useChatUI = (isSuccess, lastUserMessageId, activeChatId) => {
  const [notification, setNotification] = useState(null);
  const [pendingContext, setPendingContext] = useState([]);
  const chatBottomRef = useRef(null);
  const scrollInitialized = useRef(false);

  // EFECTO 1: Escuchar notificaciones del Backend/SDK
  useEffect(() => {
    const unsubscribe = chatEvents.on('show-notification', (msg) => {
      setNotification(msg);
      setTimeout(() => setNotification(null), 4000);
    });
    return () => unsubscribe();
  }, []);

  // EFECTO 2: Control de Scroll y Anclaje (Puntos 1 y 2 de la tabla)
  useEffect(() => {
    if (isSuccess && lastUserMessageId && !scrollInitialized.current) {
      const timer = setTimeout(() => {
        const element = document.getElementById(`msg-${lastUserMessageId}`);
        if (element) {
          element.scrollIntoView({ behavior: 'auto', block: 'start' });
          scrollInitialized.current = true;
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [isSuccess, lastUserMessageId, activeChatId]);

  // Reset del ancla cuando cambias de chat
  useEffect(() => {
    scrollInitialized.current = false;
  }, [activeChatId]);

  const scrollToBottom = () => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return {
    notification,
    pendingContext,
    setPendingContext,
    chatBottomRef,
    scrollToBottom
  };
};