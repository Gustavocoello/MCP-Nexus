import React, { useRef, useEffect } from 'react';

const MessageList = ({ messages }) => {
  const messagesEndRef = useRef(null);

  // Scroll automático al final
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((msg, index) => (
        <div key={index} className={`message ${msg.role}`}>
          <div className="message-bubble" dangerouslySetInnerHTML={{ __html: msg.text }} />
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;