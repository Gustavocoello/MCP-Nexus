import React, { useRef, useEffect } from 'react';

const MessageList = ({ messages }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages
        .filter(msg => msg.text)
        .map((msg) => (
          <div key={msg.id} className={`message ${msg.role}`}>
            <div className="message-bubble" dangerouslySetInnerHTML={{ __html: msg.text }} />
          </div>
        ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;