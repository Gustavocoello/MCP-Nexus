import React, { useState, useEffect } from 'react';
import SearchBar from '../../components/ui/SearchBar';
import MessageList from './components/MessageList/MessageList';
import { TbMessagePlus } from "react-icons/tb";
import MarkdownIt from 'markdown-it';
//import onPrompt from '../components/service/chatService';
import { getAllChats, getChatMessages, createChat, sendMessage } from '../../service/chatService';

const md = new MarkdownIt();

const ChatPage = () => {
  // Funciones auxiliares
  const loadAllChats = async () => {
  try {
    const chats = await getAllChats(); // Llama al backend
    return chats;
  } catch (error) {
    console.error('Error cargando chats:', error);
    return [];
  } 
};

  // Estados
  const [messages, setMessages] = useState([]);
  const [isJarvisTyping, setIsJarvisTyping] = useState(false);
  const [hasSentMessage, setHasSentMessage] = useState(false);
  const [activeChatId, setActiveChatId] = useState(null);

  // Efecto: Inicializar chat activo al cargar
  useEffect(() => {
  const initChat = async () => {
    const allChats = await loadAllChats();
    if (allChats.length === 0) return;

    const savedChatId = localStorage.getItem('activeChatId');
    let chatToLoad = allChats.find(chat => chat.id === savedChatId);

    if (!chatToLoad) {
      chatToLoad = allChats[0]; // fallback: primer chat si no se encontró el guardado
    }

  const rawMessages = await getChatMessages(chatToLoad.id);

  const formatted = rawMessages.map(m => ({
    id:   m.id,
    role: m.role,
    html: md.render(m.content || '')   // ⬅️  misma lógica que usas en Sidebar
  }));

  setActiveChatId(chatToLoad.id);
  setMessages(formatted);
    localStorage.setItem('activeChatId', chatToLoad.id); // aseguramos persistencia
  };

  initChat();
}, []);

  // Efecto: Escuchar eventos de carga de chat
  useEffect(() => {
  const handleChatLoaded = (event) => {
    const { chatId, messages } = event.detail; // Listo los mensajes

    setActiveChatId(chatId);
    setMessages(messages); 
    localStorage.setItem('activeChatId', chatId); // Guardar el ID del chat activo
  };

  window.addEventListener('chat-loaded', handleChatLoaded);
  return () => window.removeEventListener('chat-loaded', handleChatLoaded);
}, []);

// Efecto: Cargar el último chat al iniciar  
useEffect(() => {
  const lastChatId = localStorage.getItem("lastChatId");
  if (lastChatId) {
    window.dispatchEvent(new CustomEvent('chat-loaded', {
      detail: { chatId: parseInt(lastChatId) }
    }));
  }
}, []);


// Función para crear nuevo chat
const createNewChat = async () => {
try {
  const newChat = await createChat({}); // Backend genera el ID
  const emptyMessages = [];

  setActiveChatId(newChat.id);
  setMessages(emptyMessages);
  setHasSentMessage(false);

  // Notificar cambios
  window.dispatchEvent(new CustomEvent('chats-updated', {
  detail: { newChatId: newChat.id }
  }));

} catch (error) {
  console.error('Error creando chat:', error);
}
};

  // Manejar nuevos mensajes
  const handleNewMessage = async (message) => {
  if (message.role === 'user') {
    const jarvisTempId = `jarvis-${Date.now()}`;

    // --- USER ---------------------------------------------------------------
    const userContent = message.content ?? message.text ?? '';
    const userHtml    = md.render(userContent);

    setMessages(prev => [
      ...prev,
      { id: `user-${Date.now()}`, role: 'user', html: userHtml },
      { id: jarvisTempId,  role: 'assistant', html: '' }
    ]);

    setHasSentMessage(true);
    setIsJarvisTyping(true);

    try {
      // envía SIEMPRE el mismo campo al backend
      const response   = await sendMessage(activeChatId, userContent);
      const replyText = typeof response.reply === 'string' ? response.reply : '';
      
      const jarvisHtml = md.render(replyText);    
 

      // --- JARVIS -----------------------------------------------------------
      setMessages(prev =>
        prev.map(msg =>
          msg.id === jarvisTempId ? { ...msg, html: jarvisHtml } : msg
        )
      );
    } catch (err) {
      console.error(err);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === jarvisTempId
            ? { ...msg, html: 'Error al procesar la solicitud.' }
            : msg
        )
      );
    } finally {
      setIsJarvisTyping(false);
    }
  }
};



  return (
    <div className="page">
      <button className="new-chat-button" onClick={createNewChat}>
        <TbMessagePlus size={23} />
      </button>

      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '15px' }}>
        <img src="/icons/jarvis00.png" alt="Jarvis Icon" style={{ width: '140px', height: '80px' }} />
        <h1>Hi, I'm Jarvis.</h1>
      </div>

      <h4>How can I help you today?</h4>

      <MessageList messages={messages || []}/>

      {isJarvisTyping && (
        <div className="typing-indicator">
          Jarvis está escribiendo...
        </div>
      )}

      <SearchBar 
        onSearch={(userQuery) => handleNewMessage({ role: 'user', text: userQuery })}
        showIcon={hasSentMessage}
      />
    </div>
  );
};

export default ChatPage;