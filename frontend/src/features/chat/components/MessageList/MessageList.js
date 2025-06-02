import React, { useRef, useEffect } from 'react';

const MessageList = ({ messages = [] }) => {
  const messagesEndRef = useRef(null);

  const isBot = messages.role === 'assistant' || messages.role === 'jarvis';

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="message-list">
      {messages.map((msg, index) => (
        <div key={msg.id || index} className={`message ${msg.role}`}>
          <div
            className="message-bubble"
            dangerouslySetInnerHTML={{ __html: msg.html }}
          />
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};


export default MessageList;