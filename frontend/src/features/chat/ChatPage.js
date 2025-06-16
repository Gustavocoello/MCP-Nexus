import React, { useState, useEffect, useCallback, useRef } from 'react';
import MarkdownIt from 'markdown-it';
import { TbMessagePlus } from "react-icons/tb";
import { sendMessage } from '../../service/api_service';
import MessageList from './components/MessageList/MessageList';
import SearchBar from '../../components/ui/SearchBar/SearchBar';
import { getAllChats, getChatMessages, createChat} from '../../service/chatService';

// Cambiando de Markdown a HTML
const md = new MarkdownIt({
  html: true,
  linkify: true,

});

//  Contiene todos componentes efectos de la interfaz de Jarvis
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
  const [abortController, setAbortController] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const chatBottomRef = useRef(null);


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

  const formatted = rawMessages.map(m => {
  if (m.role === 'assistant') {
    return {
      id: m.id,
      role: m.role,
      html: md.render(m.content || '')
    };
  } else {
    // texto plano para el usuario
    const userHtml = (m.content || '')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;/');

    return {
      id: m.id,
      role: m.role,
      html: `<p>${userHtml}</p>`
    };
  }
});


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

  // Cada vez que cambia el chat activo, actualiza localStorage
  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem('activeChatId', activeChatId);
    }
  }, [activeChatId]);

// Función para crear nuevo chat
const createNewChat = async () => {
try {
  const newChat = await createChat({}); // Backend genera el ID
  const emptyMessages = [];

  setActiveChatId(newChat.id);
  localStorage.setItem('activeChatId', newChat.id);
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

  // Para manejar el stop generation
    const handleStopGeneration = () => {
    if (abortController) {
      abortController.abort();

      setIsStreaming(false);
      setIsJarvisTyping(false);
    }
  }; 

  const handleNewMessage = useCallback(async (message) => {
  if (message.role !== 'user') return;

  const controller = new AbortController();
  setAbortController(controller);
  setIsStreaming(true);
  const userContent = message.content ?? message.text ?? '';
  const jarvisTempId = `jarvis-${Date.now()}`;

  // Cambio clave aquí: Para el usuario, usamos texto plano sin markdown
  const userHtml = userContent
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;'); // <-- Eliminamos md.render() para el usuario

  setMessages(prev => [
    ...prev,
    { id: `user-${Date.now()}`, role: 'user', content: userContent, html: `<p>${userHtml}</p>` }, // <-- Aquí va el texto plano
    { id: jarvisTempId, role: 'assistant', html: '' }
  ]);

  setHasSentMessage(true);
  setIsJarvisTyping(true);

  try {
    let fullReply = '';

    await sendMessage(activeChatId, userContent, (partial) => {
      fullReply = partial;
      const jarvisHtml = md.render(fullReply); // <-- Para Jarvis mantenemos markdown
      setMessages(prev =>
        prev.map(msg => msg.id === jarvisTempId ? { ...msg, html: jarvisHtml } : msg)
      );
    }, controller.signal);

  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error(err);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === jarvisTempId
            ? { ...msg, html: 'Error al procesar la solicitud.' }
            : msg
        )
      );
    }
  } finally {
    setIsJarvisTyping(false);
    setIsStreaming(false);
    setAbortController(null);
  }
}, [activeChatId]);

  // Funcion para scrollear directamente al final
  const scrollToBottom = () => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };


  return (
  <div className="page">
    {/* Botón de nuevo chat */}
    <button className="new-chat-button" onClick={createNewChat}>
      <TbMessagePlus size={23} />
    </button>

    {/* Área de contenido */}
    <div className="content-area">
      {/* Encabezado */}
      <div className="jarvis-header">
        <img src="/icons/jarvis00.png" alt="Jarvis Icon" className="jarvis-logo1" />
        <h1 className="jarvis-title">Hi, I'm Jarvis.</h1>
      </div>

      {/* Mensaje de bienvenida */}
      <h4>How can I help you today?</h4>

      {/* Lista de mensajes */}
      <MessageList messages={messages || []} />
      <div ref={chatBottomRef}/>  {/*DIV vacío para controlar el scroll */ }

      {/* Indicador de escritura */}
      {isJarvisTyping && (
        <div className="typing-indicator">Jarvis está escribiendo...</div>
      )}
    </div>

    {/* Barra de búsqueda / entrada */}
    <SearchBar 
      onSearch={(userQuery) => handleNewMessage({ role: 'user', text: userQuery })}
      showIcon={hasSentMessage}
      isStreaming={isStreaming}
      onStop={handleStopGeneration}
      onScrollToBottom={scrollToBottom}
    />
  </div>
);

}

export default ChatPage;