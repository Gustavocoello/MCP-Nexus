// components/ChatMenu.js
import React from 'react';


const ChatMenu = ({ chatId, position, onDelete, onClose }) => {
  return (
    <div
      className="menu-contextual"
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`
      }}
    >
      {/* Opciones actuales y futuras */}
      <button
        className="menu-option"
        onClick={() => {
          onDelete(chatId);
          onClose();
        }}
      >
        Delete
      </button>

      <button className="menu-option" disabled title="Proximamente">
        Pin Chat 📌
      </button>
      <button className="menu-option" disabled title="Proximamente">
        Rename ✏️
      </button>
      <button className="menu-option" disabled title="Proximamente">
        Export 📄
      </button>
    </div>
  );
};

export default ChatMenu;
