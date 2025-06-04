import React, { useEffect, useRef } from 'react';
import { MdDeleteSweep, MdDriveFileRenameOutline } from 'react-icons/md';
import './ChatMenu.css';

const ChatMenu = ({ chatId, position, onDelete, onClose }) => {
  const menuRef = useRef(null);
  //const isMobile = window.innerWidth <= 768;

  useEffect(() => {
    // Handler para clicks fuera del menú
    const handleClickOutside = (event) => {
      // Si el click NO fue dentro del menú ni en el botón que lo abrió
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        // Verificar si el click fue en el botón de los 3 puntos
        const moreButtons = document.querySelectorAll('.more-button');
        let clickedOnMoreButton = false;
        
        moreButtons.forEach(button => {
          if (button.contains(event.target)) {
            clickedOnMoreButton = true;
          }
        });

        // Solo cerrar si no fue en un botón de los 3 puntos
        if (!clickedOnMoreButton) {
          onClose();
        }
      }
    };

    // Temporizador para evitar cerrar inmediatamente al abrir
    const timer = setTimeout(() => {
      document.addEventListener('click', handleClickOutside);
    }, 10);

    return () => {
      clearTimeout(timer);
      document.removeEventListener('click', handleClickOutside);
    };
  }, [onClose]);

  return (
    <div
      className="menu-contextual"
      ref={menuRef}
      style={{
        top: `${position.top}px`,
        left: `${position.left}px`
      }}
    >

      <button 
        className="menu-option rename-option" 
        disabled 
        onClick={(e) => e.stopPropagation()}
        title="Próximamente"
      >
        <MdDriveFileRenameOutline className="icon" />
        <span>Rename</span>
      </button>
      
      <button
        className="menu-option delete-option"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(chatId);
          onClose();
        }}
      >
        <MdDeleteSweep className="icon" />
        <span>Delete</span>
      </button>
    </div>
  );
};

export default ChatMenu;