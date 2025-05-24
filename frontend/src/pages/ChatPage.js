import React, { useState, useEffect } from 'react';
import SearchBar from '../components/SearchBar';
import MessageList from '../components/MessageList';
import onPrompt from '../components/service/api_service';
import { TbMessagePlus } from "react-icons/tb";
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt();

const ChatPage = () => {
  // Funciones auxiliares
  const loadAllChats = () => {
    const saved = localStorage.getItem('allChats');
    return saved ? JSON.parse(saved) : [];
  };

  // Generadores de IDs
  const generateChatId = () => {
    return `chat-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`;
  };

  const generateMessageId = (role) => {
    return `${role}-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`;
  };

  // Estados
  const [messages, setMessages] = useState([]);
  const [isJarvisTyping, setIsJarvisTyping] = useState(false);
  const [hasSentMessage, setHasSentMessage] = useState(false);
  const [activeChatId, setActiveChatId] = useState(null);

  // Efecto: Inicializar chat activo al cargar
  useEffect(() => {
  const allChats = loadAllChats();
  const storedActiveChatId = localStorage.getItem('activeChatId');

  if (storedActiveChatId) {
    const targetChat = allChats.find(chat => chat.id === storedActiveChatId);
    if (targetChat) {
      setMessages(targetChat.messages);
      setActiveChatId(storedActiveChatId);
    } else if (allChats.length > 0) {
      setActiveChatId(allChats[0].id);
      setMessages(allChats[0].messages);
    }
  } else if (allChats.length > 0) {
    setActiveChatId(allChats[0].id);
    setMessages(allChats[0].messages);
  } else {
    setMessages([]);
  }
}, []);

  // Efecto: Escuchar eventos de carga de chat
  useEffect(() => {
    const handleChatLoaded = (event) => {
      const { chatId } = event.detail;
      const allChats = loadAllChats();
      const targetChat = allChats.find(chat => chat.id === chatId);

      if (targetChat) {
        // Mover chat al final y actualizar estados
        const updatedChats = allChats.filter(chat => chat.id !== chatId);
        updatedChats.push(targetChat);
        
        localStorage.setItem('allChats', JSON.stringify(updatedChats));
        setActiveChatId(chatId);
        setMessages(targetChat.messages);
      }
    };

    window.addEventListener('chat-loaded', handleChatLoaded);
    return () => window.removeEventListener('chat-loaded', handleChatLoaded);
  }, []);

// Efecto: Guardar mensajes automáticamente y actualizar fecha
useEffect(() => {
  if (!activeChatId) return;

  const allChats = loadAllChats();
  const activeChat = allChats.find(chat => chat.id === activeChatId);

  if (activeChat) {
    // 1. Crear copia actualizada del chat activo
    const updatedChat = {
      ...activeChat,
      messages: messages,
      date: new Date().toISOString() // Fecha actualizada
    };

    // 2. Filtrar el chat viejo y añadir la versión actualizada al final
    const updatedChats = [
      ...allChats.filter(chat => chat.id !== activeChatId),
      updatedChat
    ];

    // 3. Guardar en localStorage y notificar cambios
    localStorage.setItem('allChats', JSON.stringify(updatedChats));
    window.dispatchEvent(new Event('chats-updated'));
  }
}, [messages, activeChatId]);


  // Función para crear nuevo chat
  const createNewChat = () => {

    const newChat = {
      id: generateChatId(),
      date: new Date().toISOString(),
      messages: []
    };

    const updatedChats = [...loadAllChats(), newChat];
    localStorage.setItem('allChats', JSON.stringify(updatedChats));
    
    setActiveChatId(newChat.id);
    setMessages([]);
    setHasSentMessage(false);
    
    // Notificar a otros componentes
    window.dispatchEvent(new Event('chats-updated'));
  };

  // Manejar nuevos mensajes
  const handleNewMessage = async (message) => {
    if (message.role === 'user') {
      const userMessageId = generateMessageId('user');
      const jarvisMessageId = generateMessageId('jarvis');

      // Agregar mensajes temporalmente
      setMessages(prev => [
        ...prev,
        { id: userMessageId, role: 'user', text: message.text },
        { id: jarvisMessageId, role: 'jarvis', text: '' }
      ]);

      setHasSentMessage(true);
      setIsJarvisTyping(true);

      try {
        // Obtener respuesta de la API
        const response = await onPrompt(message.text);
        const htmlResult = md.render(response.result || '');

        // Actualizar mensaje de Jarvis
        setMessages(prev => prev.map(msg => 
          msg.id === jarvisMessageId ? { ...msg, text: htmlResult } : msg
        ));
      } catch (error) {
        console.error(error);
        setMessages(prev => prev.map(msg => 
          msg.id === jarvisMessageId ? { ...msg, text: 'Error al procesar la solicitud' } : msg
        ));
      } finally {
        setIsJarvisTyping(false);
      }
    }
    
  };

  return (
    <div className="page">
      <button className="new-chat-button" onClick={createNewChat}>
        <TbMessagePlus size={23} />
      </button>

      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '15px' }}>
        <img src="/icons/jarvis00.png" alt="Jarvis Icon" style={{ width: '140px', height: '80px' }} />
        <h1>Hi, I'm Jarvis.</h1>
      </div>

      <h4>How can I help you today?</h4>

      <MessageList messages={messages} />

      {isJarvisTyping && (
        <div className="typing-indicator">
          Jarvis está escribiendo...
        </div>
      )}

      <SearchBar 
        onSearch={(userQuery) => handleNewMessage({ role: 'user', text: userQuery })}
        showIcon={hasSentMessage}
      />
    </div>
  );
};

export default ChatPage;