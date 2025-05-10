import React, { useState } from 'react';
import SearchBarPrompt from '../components/searchBarPrompt';
import MessageList from '../components/MessageList';

const ChatPage = () => {
  const [messages, setMessages] = useState([]);

  const handleNewMessage = (message) => {
    setMessages((prev) => [...prev, message]);
  };

  return (
    <div className="page" style={{ textAlign: 'center' }}>
      {/* Icono + Título */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '15px'
      }}>
        <img 
          src="/icons/jarvis00.png" 
          alt="Jarvis Icon" 
          style={{ width: '140px', height: '80px' }} 
        />
        <h1>Hi, I'm Jarvis.</h1>
      </div>

      <h4>How can I help you today?</h4>

      {/* Historial de mensajes */}
      <MessageList messages={messages} />

      {/* Campo de búsqueda */}
      <SearchBarPrompt onNewMessage={handleNewMessage} />
    </div>
  );
};

export default ChatPage;