import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaChartBar, FaCog, FaBars } from 'react-icons/fa';
import dayjs from 'dayjs';
import MarkdownIt from 'markdown-it';
import { CgMoreAlt } from "react-icons/cg";
import AnimatedJarvis from '../../ui/AnimatedJarvis';
import ChatMenu from '../../../features/chat/components/ChatMenu/ChatMenu';
import useCurrentUser from '../../../features/auth/components/context/useCurrentUser';
import '../Sidebar/Sidebar.css';

// Servicios
import { getAllChats, getChatMessages, deleteChat } from '../.././../service/chatService';

const md = new MarkdownIt();

const Sidebar = () => {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(false); 
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [menuPosition, setMenuPosition] = useState({ top: 0, left: 0 });
  const { user, loading } = useCurrentUser();
  // Cargar los chats desde localStorage
  const fetchAndSetChats = async () => {
  try {
    const fetchedChats = await getAllChats();
    const chatsConTitulo = fetchedChats.map(chat => ({
      ...chat,
      title: chat.title && chat.title.trim() !== '' ? chat.title : 'Sin título',
      date: chat.updated_at || chat.created_at
    }));
    setChats(chatsConTitulo);
  } catch (error) {
    console.error('Error cargando chats:', error);
  }
};

useEffect(() => {
  window.dispatchEvent(new CustomEvent('sidebar-toggled', { detail: { isOpen } }));
}, [isOpen]);

useEffect(() => {
  if (user && !loading) {
    fetchAndSetChats();
  }
}, [user, loading]);


useEffect(() => {
  fetchAndSetChats();
}, []);

useEffect(() => {
  const handleChatsUpdated = () => {
    fetchAndSetChats();
  };

  window.addEventListener('chats-updated', handleChatsUpdated);
  return () => window.removeEventListener('chats-updated', handleChatsUpdated);
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

  // Borrar un chat
  const handleDeleteChat = async (chatId) => {
  try {
    // Llamar al backend para eliminar el chat
    await deleteChat(chatId);

    // Actualizar estado local
    const updatedChats = chats.filter(chat => chat.id !== chatId);
    setChats(updatedChats);

    // Si eliminé el chat que estaba abierto, borro la referencia
  if (localStorage.getItem('activeChatId') === chatId) {
    localStorage.removeItem('activeChatId');
  }

    // Si es el chat activo, limpiar
    if (currentChatId === chatId) {
      setCurrentChatId(null);
      localStorage.removeItem('activeChatId'); // Opcional: si aún usas localStorage para algo
      window.dispatchEvent(new CustomEvent('chat-loaded', { detail: { chatId } }));
    }
  } catch (error) {
    console.error('Error eliminando chat:', error);
  }
};
  
  const [showMenu, setShowMenu] = useState(null);

  const toggleMenu = (chatId, event) => {
  // Detener la propagación solo si hay un evento (evita errores)
  if (event) {
    event.stopPropagation();
    
    // Solo calcula la posición si el menú se va a abrir (no cerrar)  
    if (showMenu !== chatId) {
      const rect = event.currentTarget.getBoundingClientRect();
      setMenuPosition({
        top: rect.bottom + window.scrollY,
        left: rect.right + window.scrollX,
      });
    }
  }

  // Alternar visibilidad del menú
  setShowMenu(showMenu === chatId ? null : chatId);
};

  // Cargar mensajes del chat seleccionado
  const handleLoadChat = async (chatId) => {
  try {
    // Cargar mensajes del chat desde backend
    const rawMessages = await getChatMessages(chatId);

    // Actualizar chat activo
    setCurrentChatId(chatId);

    const messages = rawMessages.map(m => ({
      id:   m.id,
      role: m.role,
      html: md.render(m.content || '')   // convierte Markdown → HTML
    }));

    // Disparar evento para cargar mensajes en ChatPage
    // console.log("Mensajes desde backend:", messages); 
    window.dispatchEvent(new CustomEvent('chat-loaded', {
      detail: { chatId, messages }
      
    }));
  } catch (error) {
    console.error('Error cargando chat:', error);
  }
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

                    {groupChats.map((chat) => (
                      <div key={chat.id} className="chat-item-container">
                        <button
                          className={`sidebar-chat-item ${chat.id === currentChatId ? 'active' : ''}`}
                          onClick={() => handleLoadChat(chat.id)}
                        >
                          <span className="label">{chat.title || "Sin título"}</span>
                          </button>

                        {chat.id === currentChatId && (
                          <button
                            className="more-button"
                            onClick={(e) => {
                              e.stopPropagation();
                              toggleMenu(chat.id, e);
                            }}
                          >
                            <CgMoreAlt size={18} />
                          </button>
                        )}
                        {showMenu === chat.id && (
                          <ChatMenu
                            chatId={chat.id}
                            position={menuPosition}
                            onDelete={handleDeleteChat}
                            onClose={() => setShowMenu(null)}
                          />
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