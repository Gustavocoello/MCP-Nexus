import React, { useState, useEffect } from 'react';
import dayjs from 'dayjs'; // Importar dayjs
import { Link, useLocation } from 'react-router-dom';
import { FaChartBar, FaCog, FaBars } from 'react-icons/fa';
import { CgMoreAlt } from "react-icons/cg";
import AnimatedJarvis from './AnimatedJarvis';
import './Sidebar.css';


// Versión optimizada con manejo de mensajes vacíos
const getFirstUserMessage = (messages = []) => { // <-- Parámetro por defecto
  const userMessage = messages.find(msg => msg.role === "user"); // <-- find() en vez de filter()
  return userMessage?.text || "Sin mensaje"; // <-- Optional chaining
};

const Sidebar = () => {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(true); // true = abierto por defecto
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });

  // Cargar los chats desde localStorage
  useEffect(() => {
    const loadChats = () => {
      const saved = localStorage.getItem('allChats');
      return saved ? JSON.parse(saved) : [];
    };

    

    setChats(loadChats());
  }, []);

  // Escuchar cambios externos en el chat activo
useEffect(() => {
  const handleChatLoaded = (e) => {
    const { chatId } = e.detail;
    setCurrentChatId(chatId);
  };

  window.addEventListener('chat-loaded', handleChatLoaded);
  return () => {
    window.removeEventListener('chat-loaded', handleChatLoaded);
  };
}, []);

  function getChatGroup(chatDateStr) {
  const chatDate = dayjs(chatDateStr);
  const now = dayjs();
  const diffDays = now.diff(chatDate, 'day');

  if (diffDays === 0) return 'today';
  if (diffDays === 1) return 'yesterday';
  if (diffDays < 7) return 'previous7Days';
  if (diffDays < 30) return 'previous30Days';
  return 'older';
}

const categorizedChats = chats.reduce((acc, chat) => {
  const group = getChatGroup(chat.date);
  acc[group].push(chat);
  return acc;
}, {
  today: [],
  yesterday: [],
  previous7Days: [],
  previous30Days: [],
  older: []
});


  const handleDeleteChat = (chatId) => {
  const updatedChats = chats.filter(chat => chat.id !== chatId);

  setChats(updatedChats);
  localStorage.setItem('allChats', JSON.stringify(updatedChats));

  // Si eliminamos el chat activo, limpiamos el estado local y localStorage
  if (currentChatId === chatId) {
    setCurrentChatId(null);
    localStorage.removeItem('activeChatId');

    // Disparar evento para limpiar mensajes en ChatPage
    window.dispatchEvent(new CustomEvent('chat-loaded', { 
    detail: { chatId }
  }));
  }
};
  const [showMenu, setShowMenu] = useState(null);

const toggleMenu = (chatId, event) => {
  if (event && event.currentTarget) {
    const rect = event.currentTarget.getBoundingClientRect();
    setMenuPosition({
      top: rect.bottom + window.scrollY,
      left: rect.right + window.scrollX,
    });
  }

  setShowMenu(chatId === showMenu ? null : chatId);
};


  const handleLoadChat = (messages, chatId) => {
    // Guardar temporalmente en localStorage
    localStorage.setItem('tempChatToLoad', JSON.stringify(messages));
    localStorage.setItem('activeChatId', chatId);
    // Disparar evento para recargar el chat
    window.dispatchEvent(new CustomEvent('chat-loaded', { 
    detail: { chatId }
  }));
    setCurrentChatId(chatId);
  };

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      {/* Botón de toggle */}
      <div className="sidebar-toggle" onClick={() => setIsOpen(!isOpen)}>
        <FaBars size={20} />
      </div>

      {/* Logo Jarvis */}
      <div className="sidebar-upper">
        <Link 
          to="/" 
          className={`sidebar-item jarvis ${location.pathname === '/' ? 'active' : ''}`}
        >
          <div className="jarvis-logo">
            <AnimatedJarvis />
          </div>
        </Link>

        {/* Dashboard */}
        <Link 
          to="/dashboard" 
          className={`sidebar-item ${location.pathname === '/dashboard' ? 'active' : ''}`}
        >
          <FaChartBar className="icon" />
          <span className="label">Dashboard</span>
        </Link>
      </div>
      {/* Lista de chats */}
      <div className="sidebar-section">
        <div className="chats-scroll">
        <ul className="chats-list">
          {isOpen && (
            <>
              {Object.entries(categorizedChats).map(([groupKey, groupChats]) => (
                groupChats.length > 0 && (
                  <li key={groupKey}>
                    <span className="chat-category">
                      {{
                        today: 'Today',
                        yesterday: 'Yesterday',
                        previous7Days: 'Previous 7 days',
                        previous30Days: 'Previous 30 days',
                        older: 'Older'
                      }[groupKey]}
                    </span>

                    {groupChats.map((chat, index) => (
                      <div key={index} className="chat-item-container">
                        <button
                          className={`sidebar-chat-item ${chat.id === currentChatId ? 'active' : ''}`}
                          onClick={() => handleLoadChat(chat.messages, chat.id)}
                        >
                          <span className="label">{getFirstUserMessage(chat.messages)}</span>
                        </button>

                        {chat.id === currentChatId && (
                          <button
                            className="more-button"
                            onClick={(e) => toggleMenu(chat.id, e)}
                          >
                            <CgMoreAlt size={18} />
                          </button>
                        )}

                        {showMenu === chat.id && (
                          <div
                            className="menu-contextual"
                            style={{
                              top: `${menuPosition.top}px`,
                              left: `${menuPosition.left}px`,
                            }}
                          >
                            <button
                              className="delete-chat-button"
                              onClick={() => {
                                handleDeleteChat(chat.id);
                                toggleMenu(null);
                              }}
                            >
                              Delete
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </li>
                )
              ))}

              {Object.values(categorizedChats).every(group => group.length === 0) && (
                <li>
                  <span className="no-chats-message">No hay chats guardados</span>
                </li>
              )}
            </>
          )}
        </ul>
        </div>
      </div>
     
      {/* Settings */}
      <Link 
        to="/config" 
        className={`sidebar-item ${location.pathname === '/config' ? 'active' : ''}`}
      >
        <FaCog className="icon" />
        <span className="label">Settings</span>
      </Link>
    </div>
  );
};

export default Sidebar;