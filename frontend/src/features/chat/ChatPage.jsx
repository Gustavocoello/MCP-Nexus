// src/features/chat/ChatPage.jsx
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet } from 'react-router-dom';
import MarkdownIt from 'markdown-it';
import { TbMessagePlus } from "react-icons/tb";

// Componentes y Hooks
import SearchBar from '@/components/ui/SearchBar/SearchBar';
import MessageList from './components/MessageList/MessageList';
import LoginButton from '@/components/layout/LoginButton/LoginButton';
import { useAuthContext } from '@/features/auth/components/context/AuthContext';
import useChatMessages from '../chat/hooks/useChatMessages';
import { useChatActions } from '../chat/hooks/useChatActions';
import { useChatUI } from '../chat/hooks/useChatUI';
import { getAllChats, createChat, updateChatTitle } from '../../service/chatService';
import { chatEvents } from '../chat/utils/chatEvents';
import { storageAdapter } from '../chat/utils/storageAdapter';
import { streamLogger } from '@/components/controller/log/logger.jsx';
import { useChatState } from '../chat/hooks/useChatState';
import { isApiReady } from '@/service/api';

const md = new MarkdownIt({ html: false, linkify: true });

const ChatPage = ({ 
  guest = false, 
  onUnauthorized = () => console.warn("Login required"),
  renderLogo = null 
}) => {
  const { user, isAuthenticated } = useAuthContext();

  // --- HOOKS PERSONALIZADOS ---
  const {
    activeChatId,
    setActiveChatId,
    localMessages,
    setLocalMessages,
    hasSentMessage,
    setHasSentMessage
  } = useChatState();

  const { 
    messages: cachedMessages, 
    appendMessageToCache, 
    updateMessageInCache, 
    lastUserMessageId, 
    isSuccess 
  } = useChatMessages(activeChatId, { keep: 10 });

  const { 
    handleNewMessage, 
    isJarvisTyping, 
    isStreaming, 
    stopGeneration 
  } = useChatActions(activeChatId, isAuthenticated, { appendMessageToCache, updateMessageInCache, md });

  const {
    notification,
    pendingContext,
    setPendingContext,
    chatBottomRef,
    scrollToBottom
  } = useChatUI(isSuccess, lastUserMessageId, activeChatId);

  // --- EFECTOS DE ORQUESTACIÓN ---
  
  // 0. Proteccion desacoplada 
  useEffect(() => {
    // En lugar de usar Navigate, usamos un callback
    if (!isAuthenticated && !guest) {
      onUnauthorized();
    }
  }, [isAuthenticated, guest, onUnauthorized]);
  
  // 1. Inicialización de Chat (Punto 4)
  useEffect(() => {
    const initChat = async () => {
      if (!isAuthenticated) return; // Solo inicializamos si el usuario está autenticado
      try {
        const allChats = await getAllChats();
        if (!allChats || allChats.length === 0) return;

        const savedChatId = storageAdapter.getItem();
        const chatToLoad = allChats.find(c => c.id === savedChatId) || allChats[0];
        if (chatToLoad) {
          setActiveChatId(chatToLoad.id);
          }        
      } catch (e) { 
        streamLogger.error("Error al cargar chats iniciales:", e.message); }
    };

    const token = storageAdapter.getItem('jarvis_token');
    if (isAuthenticated && token) {
      initChat();
    } else {
      streamLogger.info(" [ChatPage] Esperando autenticación y token...");
    }
  }, [isAuthenticated, setActiveChatId]);

  // 2. Sincronizar Caché RAM -> UI Local (Punto 3 y 9)
  useEffect(() => {
    if (!cachedMessages || cachedMessages.length === 0) return;
    
    const formatted = cachedMessages.map(m => {
      if (m.role === 'assistant') {
        return { ...m, html: m.content ? md.render(m.content) : '<span class="typing-dots">...</span>' };
      }
      const safe = (m.content || '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
      return { ...m, html: `<p>${safe}</p>` };
    });

    setLocalMessages(formatted);

    // LÓGICA DE TÍTULO: Si es el primer mensaje del usuario, avisamos al Sidebar
    if (!hasSentMessage && formatted.length > 0) {
      setHasSentMessage(true);
      // Emitimos evento para que el Sidebar recargue y vea el nuevo chat/título
      chatEvents.emit('chats-updated');
    }
  }, [cachedMessages, hasSentMessage]);

  // 3. Escuchar Sidebar (Punto 6)
  useEffect(() => {
    const unsubscribe = chatEvents.on('chat-loaded', (data) => {
      if (data?.chatId) setActiveChatId(data.chatId);
    });
    return () => unsubscribe();
  }, []);

  // 4. Limpieza de anónimos (Punto 8)
  useEffect(() => {
    if (isAuthenticated) localStorage.removeItem('anonMessageCount');
  }, [isAuthenticated]);

  // 5. Persistencia ID (Punto 5)
  useEffect(() => {
    if (activeChatId) storageAdapter.setItem(activeChatId);
  }, [activeChatId]);

  // 6. Si el ID cambia a null (nuevo chat), limpiamos la pantalla
  useEffect(() => {
    if (!activeChatId) {
      setLocalMessages([]);
    }
  }, [activeChatId]);

  const createNewChat = async () => {
    try {
      const newChat = await createChat({ title: "Nuevo Chat" });

      setActiveChatId(newChat.id);
      setLocalMessages([]);
      setHasSentMessage(false);
      storageAdapter.setItem(newChat.id);
      chatEvents.emit('chats-updated', { chatId: newChat.id });
      streamLogger.info("Nuevo chat creado y pantalla limpia.");
    } catch (error) {
      streamLogger.error("Error creando nuevo chat:", error);
    }
  };
  
  return (
    <div className="page">
      {!isAuthenticated && <LoginButton />}
      {isAuthenticated && (
        <button className="new-chat-button" onClick={createNewChat}>
          <TbMessagePlus size={23} />
        </button>
      )}

      <div className="content-area">
        <div className="jarvis-header">
          <img src="/icons/jarvis00.png" alt="Jarvis" className="jarvis-logo1" />
          <h1 className="jarvis-title">Hi, I'm Jarvis.</h1>
        </div>
        <h4>How can I help you today?</h4>

        <MessageList messages={localMessages} />
        <div ref={chatBottomRef} />

        {isJarvisTyping && <div className="typing-indicator">Jarvis está escribiendo...</div>}
      </div>

      <SearchBar 
        onSearch={async (query, context, img, tool) => {
          let currentChatId = activeChatId;

          // 1. SI NO HAY CHAT ACTIVO, LO CREAMOS PRIMERO
          if (!currentChatId || currentChatId === 'null') {
            // CASO A: USUARIO AUTENTICADO (ID REAL - LLAMA A createChat del Backend)
            if (isAuthenticated) {
              try {
                streamLogger.info("Creando chat en DB para usuario autenticado...");
                const newChat = await createChat({ title: query.trim().substring(0, 30) });
                currentChatId = newChat.id;
                chatEvents.emit('chats-updated', { chatId: currentChatId });
              } catch (error) {
                streamLogger.error("Error al crear chat en DB", error);
                return;
              }
            } 
            // CASO B: INVITADO (ID Temporal - NO llama a createChat de Clerk)
            else {
              streamLogger.info("Generando ID temporal para invitado...");
              currentChatId = `guest_${Date.now()}`; // Generamos un ID local
              // No emitimos chats-updated porque no hay backend que refrescar
            }
            setActiveChatId(currentChatId);
            storageAdapter.setItem(currentChatId);
          }
          // El chat existe (se creó con el botón +) pero no tiene nombre real
          else if (isAuthenticated && !hasSentMessage) {
            try {
              await updateChatTitle(currentChatId, query.substring(0, 30));
              chatEvents.emit('chats-updated', { chatId: currentChatId });
              setHasSentMessage(true); // Para que no vuelva a intentar renombrar
            } catch (err) {
              console.error("No se pudo actualizar el título", err);
            }
          }
          // 3. Enviamos el mensaje normalmente
          handleNewMessage({ role: 'user', text: query }, context, img, tool, currentChatId);
        }}
        onContextExtracted={(entry) => setPendingContext(prev => [...prev, entry])}
        onClearContext={() => setPendingContext([])}
        onRemoveContext={(name) => setPendingContext(prev => prev.filter(c => c.name !== name))}
        pendingContext={pendingContext}
        showIcon={hasSentMessage}
        isStreaming={isStreaming}
        onStop={stopGeneration}
        onScrollToBottom={scrollToBottom}
      />

      {notification && <div className="notification-memory">{notification}</div>}
      <Outlet />
    </div>
  );
};

export default ChatPage;