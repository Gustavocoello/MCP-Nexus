import React, { useState } from 'react';
import SearchBar from '../components/SearchBar';
import MessageList from '../components/MessageList';
import onPrompt from '../components/service/api_service';
import { TbMessagePlus } from "react-icons/tb";
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt();

const ChatPage = () => {
  const [messages, setMessages] = useState([]);
  const [messageIdCounter, setMessageIdCounter] = useState(0);
  const [isJarvisTyping, setIsJarvisTyping] = useState(false);
  const [hasSentMessage, setHasSentMessage] = useState(false);

  const handleNewMessage = async (message) => {
    if (message.role === 'user') {
      // Generar IDs únicos
      const userMessageId = messageIdCounter;
      const tempMessageId = messageIdCounter + 1;

      // Agregar mensaje del usuario
      setMessages(prev => [
        ...prev,
        { 
          id: `user-${userMessageId}`, 
          role: 'user', 
          text: message.text 
        }
      ]);

      // Agregar mensaje temporal de carga
      setMessages(prev => [
        ...prev,
        { 
          id: `jarvis-${tempMessageId}`, 
          role: 'jarvis', 
          text: '' 
        }
      ]);

      setMessageIdCounter(prev => prev + 2);
      setHasSentMessage(true);
      setIsJarvisTyping(true);

      try {
        // Llamar a la API
        const response = await onPrompt(message.text);
        
        // Convertir a HTML
        const htmlResult = md.render(response.result || '');
        
        // Actualizar mensaje temporal
        setMessages(prev => prev.map(msg => 
          msg.id === `jarvis-${tempMessageId}`
            ? { ...msg, text: htmlResult }
            : msg
        ));
      } catch (error) {
        console.error(error);
        setMessages(prev => prev.map(msg => 
          msg.id === `jarvis-${tempMessageId}`
            ? { ...msg, text: 'Error al procesar la solicitud' }
            : msg
        ));
      } finally {
        setIsJarvisTyping(false);
      }
    }
  };

  return (
    <div className="page">
      {/* Botón para nuevo chat */}
      <button className="new-chat-button" onClick={() => { 
        setMessages([]); 
        setHasSentMessage(false);
      }}>
        <TbMessagePlus size={23} />
      </button>
      {/* Cabecera */}
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '15px' }}>
        <img src="/icons/jarvis00.png" alt="Jarvis Icon" style={{ width: '140px', height: '80px' }} />
        <h1>Hi, I'm Jarvis.</h1>
      </div>

      <h4>How can I help you today?</h4>

      {/* Lista de mensajes */}
      <MessageList messages={messages} />

      {/* Indicador de escritura */}
      {isJarvisTyping && (
        <div className="typing-indicator">
          Jarvis está escribiendo...
        </div>
      )}

      {/* Barra de búsqueda */}
      <SearchBar 
      onSearch={(userQuery) => handleNewMessage({ role: 'user', text: userQuery })}
      showIcon={hasSentMessage}/>
    </div>
  );
};

export default ChatPage;