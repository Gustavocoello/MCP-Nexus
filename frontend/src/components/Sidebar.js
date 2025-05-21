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
  

  // Función para categorizar los chats
  const categorizeChats = (chats) => {
    const categorizedChats = {
      today: [],
      yesterday: [],
      previous7Days: [],
      previous30Days: [],
      older: []
    };

    chats.forEach((chat) => {
      const chatDate = dayjs(chat.date);
      const today = dayjs();

      if (today.isSame(chatDate, 'day')) {
        categorizedChats.today.push(chat);
      } else if (today.subtract(1, 'day').isSame(chatDate, 'day')) {
        categorizedChats.yesterday.push(chat);
      } else if (today.subtract(7, 'day').isSameOrBefore(chatDate, 'day')) {
        categorizedChats.previous7Days.push(chat);
      } else if (today.subtract(30, 'day').isSameOrBefore(chatDate, 'day')) {
        categorizedChats.previous30Days.push(chat);
      } else {
        categorizedChats.older.push(chat);
      }
    });

    return categorizedChats;
  };

  const handleDeleteChat = (chatId) => {
  const updatedChats = chats.filter(chat => chat.id !== chatId);

  setChats(updatedChats);
  localStorage.setItem('allChats', JSON.stringify(updatedChats));

  // Si eliminamos el chat activo, limpiamos el estado local y localStorage
  if (currentChatId === chatId) {
    setCurrentChatId(null);
    localStorage.removeItem('tempChatToLoad');
    localStorage.removeItem('activeChatId');

    // Disparar evento para limpiar mensajes en ChatPage
    window.dispatchEvent(new Event('chat-loaded'));
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

  // Categorizar los chats
  const categorizedChats = categorizeChats(chats);

  const handleLoadChat = (messages, chatId) => {
    // Guardar temporalmente en localStorage
    localStorage.setItem('tempChatToLoad', JSON.stringify(messages));
    // Disparar evento para recargar el chat
    window.dispatchEvent(new Event('chat-loaded'));
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
  <ul className="chats-list">
    {/* Mostrar chats solo si el sidebar está abierto */}
    {isOpen && (
      <>
        {/* Chats de hoy */}
{categorizedChats.today.map((chat, index) => (
  <div key={index} className="chat-item-container">
    <button
      className={`sidebar-chat-item ${chat.id === currentChatId ? 'active' : ''}`}
      onClick={() => handleLoadChat(chat.messages, chat.id)}
    >
      <span className="label">
        {getFirstUserMessage(chat.messages)}
      </span>
    </button>

    {/* Icono de 3 puntos solo en el chat activo */}
    {chat.id === currentChatId && (
      <button
        className="more-button"
        onClick={(e) => toggleMenu(chat.id, e)}
      >
        <CgMoreAlt size={18} />
      </button>
    )}
    {/* Menú contextual */}
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
        {/* Chats de ayer */}
        {categorizedChats.yesterday.length > 0 && (
          <li>
            <span className="chat-category">Yesterday</span>
            {categorizedChats.yesterday.map((chat, index) => (
              <button
                key={index}
                className={`sidebar-chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleLoadChat(chat.messages, chat.id)}
              >
                <span className="label">
                  {getFirstUserMessage(chat.messages)}
                </span>
              </button>
            ))}
          </li>
        )}

        {/* Chats de los últimos 7 días */}
        {categorizedChats.previous7Days.length > 0 && (
          <li>
            <span className="chat-category">Previous 7 days</span>
            {categorizedChats.previous7Days.map((chat, index) => (
              <button
                key={index}
                className={`sidebar-chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleLoadChat(chat.messages, chat.id)}
              >
                <span className="label">
                  {getFirstUserMessage(chat.messages)}
                </span>
              </button>
            ))}
          </li>
        )}

        {/* Chats de los últimos 30 días */}
        {categorizedChats.previous30Days.length > 0 && (
          <li>
            <span className="chat-category">Previous 30 days</span>
            {categorizedChats.previous30Days.map((chat, index) => (
              <button
                key={index}
                className={`sidebar-chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleLoadChat(chat.messages, chat.id)}
              >
                <span className="label">
                  {getFirstUserMessage(chat.messages)}
                </span>
              </button>
            ))}
          </li>
        )}

        {/* Chats antiguos */}
        {categorizedChats.older.length > 0 && (
          <li>
            <span className="chat-category">Older</span>
            {categorizedChats.older.map((chat, index) => (
              <button
                key={index}
                className={`sidebar-chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                onClick={() => handleLoadChat(chat.messages, chat.id)}
              >
                <span className="label">
                  {getFirstUserMessage(chat.messages)}
                </span>
              </button>
            ))}
          </li>
        )}
      </>
    )}

    {/* Mensaje cuando no hay chats guardados */}
    {Object.values(categorizedChats).every(category => category.length === 0) && (
      <li>
        <span className="no-chats-message">
          No hay chats guardados
        </span>
      </li>
    )}
    </ul>
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