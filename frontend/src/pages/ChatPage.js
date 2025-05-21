import React, { useState, useEffect } from 'react';
import SearchBar from '../components/SearchBar';
import MessageList from '../components/MessageList';
import onPrompt from '../components/service/api_service';
import { TbMessagePlus } from "react-icons/tb";
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt();

const ChatPage = () => {
  const loadAllChats = () => {
    const saved = localStorage.getItem('allChats');
    return saved ? JSON.parse(saved) : [];
  };

  const loadActiveChat = () => {
    const allChats = loadAllChats();
    return allChats.length > 0 ? allChats[allChats.length - 1].messages : [];
  };

  const [messages, setMessages] = useState(loadActiveChat);
  const [messageIdCounter, setMessageIdCounter] = useState(0);
  const [isJarvisTyping, setIsJarvisTyping] = useState(false);
  const [hasSentMessage, setHasSentMessage] = useState(false);

  // 👇 Escuchar evento global 'chat-loaded'
  useEffect(() => {
    const handleChatLoaded = () => {
      const tempChat = localStorage.getItem('tempChatToLoad');
      if (tempChat) {
        const parsedMessages = JSON.parse(tempChat);
        setMessages(parsedMessages);
        localStorage.removeItem('tempChatToLoad'); // Limpiar después de usarlo
      }
    };

    window.addEventListener('chat-loaded', handleChatLoaded);

    // Limpiar listener al desmontar
    return () => {
      window.removeEventListener('chat-loaded', handleChatLoaded);
      localStorage.removeItem('tempChatToLoad'); // Limpiar al desmontar
    };
  }, []);

  // 👇 Guardar cambios en messages como último chat activo
  useEffect(() => {
    const allChats = loadAllChats();

    if (allChats.length > 0) {
      allChats[allChats.length - 1].messages = messages;
    } else {
      allChats.push({ id: `chat-${Date.now()}`, messages });
    }

    localStorage.setItem('allChats', JSON.stringify(allChats));

    // Vamos a verificar que se guarda en localStorage
    console.log("Chats guardados en localStorage:", JSON.parse(localStorage.getItem('allChats')));
  }, [messages]);

  // 👇 Modificar la función createNewChat para incluir fecha
const createNewChat = () => {
  const allChats = loadAllChats();
  
  const newChat = {
    id: `chat-${Date.now()}`,
    date: new Date().toISOString(), // ¡FECHA ES CLAVE!
    messages: []
  };

  allChats.push(newChat);
  localStorage.setItem('allChats', JSON.stringify(allChats));
  setMessages([]);
  setHasSentMessage(false);
  
  // Forzar recarga del sidebar (opcional)
  window.dispatchEvent(new Event('chats-updated'));
};
  const handleNewMessage = async (message) => {
    if (message.role === 'user') {
      const userMessageId = messageIdCounter;
      const tempMessageId = messageIdCounter + 1;

      setMessages(prev => [
        ...prev,
        { id: `user-${userMessageId}`, role: 'user', text: message.text }
      ]);

      setMessages(prev => [
        ...prev,
        { id: `jarvis-${tempMessageId}`, role: 'jarvis', text: '' }
      ]);

      setMessageIdCounter(prev => prev + 2);
      setHasSentMessage(true);
      setIsJarvisTyping(true);

      try {
        const response = await onPrompt(message.text);
        const htmlResult = md.render(response.result || '');

        setMessages(prev => prev.map(msg => 
          msg.id === `jarvis-${tempMessageId}` ? { ...msg, text: htmlResult } : msg
        ));
      } catch (error) {
        console.error(error);
        setMessages(prev => prev.map(msg => 
          msg.id === `jarvis-${tempMessageId}` ? { ...msg, text: 'Error al procesar la solicitud' } : msg
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