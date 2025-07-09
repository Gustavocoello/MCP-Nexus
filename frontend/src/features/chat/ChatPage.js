import React, { useState, useEffect, useCallback, useRef } from 'react';
import MarkdownIt from 'markdown-it';
import { TbMessagePlus } from "react-icons/tb";
import { sendMessage, sendAnonymousMessage} from '../../service/api_service';
import MessageList from './components/MessageList/MessageList';
import SearchBar from '../../components/ui/SearchBar/SearchBar';
import { getAllChats, getChatMessages, createChat} from '../../service/chatService';
import useAuthStatus from '../../service/useAuthStatus';
import LoginButton from '../../components/layout/LoginButton/LoginButton';
import useCurrentUser from '../../features/auth/components/context/useCurrentUser';

// Cambiando de Markdown a HTML
const md = new MarkdownIt({
  html: false, // Antes True ahora False para no escaparse
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
  const [notification, setNotification] = useState(null);
  const [pendingContext, setPendingContext] = useState([]);
  const isAuthenticated = useAuthStatus();
  const { user, loading } = useCurrentUser();
  
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

  const handleNewMessage = useCallback(async (message, contextFromFile = '') => {
  if (message.role !== 'user') return;
   
  const controller = new AbortController();
  setAbortController(controller);
  setIsStreaming(true);
  const userContent = message.content ?? message.text ?? '';
  const jarvisTempId = `jarvis-${Date.now()}`;
  
  const combinedContext = Array.isArray(contextFromFile)
  ? contextFromFile.map(c => `🗂️ ${c.name}:\n${c.text}`).join('\n\n')
  : contextFromFile;

  const fullPrompt = combinedContext
  ? `Archivo recibido:\n${combinedContext}\n\nPregunta del usuario:\n${userContent}`
  : userContent;


  // Cambio clave aquí: Para el usuario, usamos texto plano sin markdown
  const escapeHtml = (text) =>
  text
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');

  const userHtml = `<p>${escapeHtml(userContent)}</p>`;

  if (userContent) {
    setMessages(prev => [
      ...prev,
      { id: `user-${Date.now()}`, role: 'user', content: userContent, html: `<p>${userHtml}</p>` },
      { id: jarvisTempId, role: 'assistant', html: '' }
    ]);
  } else {
    setMessages(prev => [
      ...prev,
      { id: jarvisTempId, role: 'assistant', html: '' }
    ]);
  }

  setHasSentMessage(true);
  setIsJarvisTyping(true);

  try {
    let fullReply = '';

    let res;
    // Mensajes para usuarios no logeados
    if (isAuthenticated === false) {
      const anonCount = parseInt(localStorage.getItem('anonMessageCount') || '0', 10);

      if (anonCount >= 5) {
        fullReply = "Has alcanzado el límite de 5 mensajes gratuitos. Por favor inicia sesión para continuar.";

        setMessages(prev =>
          prev.map(msg =>
            msg.id === jarvisTempId
            ? { ...msg, content: fullReply, html: '', stable: false }
            : msg
          )
        );

        showNotification("Has alcanzado el límite de mensajes gratuitos. Inicia sesión para continuar.");
        setIsJarvisTyping(false);
        setIsStreaming(false);
        return;
      }

      // ✅ Solo se hace la solicitud si no ha alcanzado el límite
      res = await sendAnonymousMessage(fullPrompt);

      // Incrementar contador después de la respuesta
      localStorage.setItem('anonMessageCount', String(anonCount + 1));
      console.log('Mensajes de usuarios no registrados:', anonCount );

      if (res.result) {
        fullReply = res.result;
      } else if (res.error) {
        fullReply = res.error;
      }

      setMessages(prev =>
        prev.map(msg =>
          msg.id === jarvisTempId
            ? { ...msg, content: fullReply, html: '', stable: false }
            : msg
        )
      );
    // Mensajes para usuarios logeados
    } else {
      res = await sendMessage({
        chatId: activeChatId,
        text: userContent,
        hidden_context: combinedContext
      }, (partial) => {
        // streaming parcial para usuarios logueados
        console.log('partial recibido:', partial);
        

        let cleanPartial = partial;

        if (partial.includes('[NOTIFICATION]')) {
          const parts = partial.split('[NOTIFICATION]');
          cleanPartial = parts[0].trim();
          const notificationText = parts[1]?.trim();
          if (notificationText) {
            showNotification(notificationText);
          }
        }

        setMessages(prev =>
          prev.map(msg =>
            msg.id === jarvisTempId
              ? { ...msg, content: cleanPartial, html: '', stable: false }
              : msg
          )
        );
      }, controller.signal);
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      console.error(err);
      setMessages(prev =>
        prev.map(msg =>
          msg.id === jarvisTempId
            ? { ...msg,
              stable:true,
               html: 'Error al procesar la solicitud.'
              }
            : msg
        )
      );
    }

  } finally {
    setIsJarvisTyping(false);
    setIsStreaming(false);
    setAbortController(null);
    setPendingContext([]);
    setMessages(prev =>
    prev.map(msg =>
      msg.id === jarvisTempId
        ? { ...msg, stable: true }
        : msg
    )
  ); 
  }
}, [activeChatId, isAuthenticated]);



  // Funcion para scrollear directamente al final
  const scrollToBottom = () => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  };

  //Funcion para mostrar la notificacion del backend - Memoria-
  const showNotification = (msg) => {
    setNotification(msg);
    setTimeout(() => setNotification(null), 4000); // <-- La notificación dura 4 segundos y desaparece
    };

  // Funcion para limpiar el contexto pendiente
  const clearPendingContext = () => {
    setPendingContext([]);
  };
  // Funcion para eliminar un contexto pendiente por nombre
  const removeContextByName = (name) => {
    setPendingContext(prev => prev.filter(ctx => ctx.name !== name));
  };

  useEffect(() => {
    if (isAuthenticated === true) {
      localStorage.removeItem('anonMessageCount');
    }
  }, [isAuthenticated]);

  if (loading) {
    console.log('Usuario actual:', user);
    return <div className="loading-screen">Cargando usuario...</div>;

  }

  return (
  <div className="page">
    {/* Botón de nuevo chat */}
    <LoginButton /> {/* ⬅ Aquí va el botón para iniciar sesion */}

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
      onSearch={(userQuery, context) => handleNewMessage({ role: 'user', text: userQuery }, context)}
      onContextExtracted={(entry) => setPendingContext(prev => [...prev, entry])}
      onClearContext={clearPendingContext}
      onRemoveContext={removeContextByName}
      pendingContext={pendingContext}
      showIcon={hasSentMessage}
      isStreaming={isStreaming}
      onStop={handleStopGeneration}
      onScrollToBottom={scrollToBottom}
    />

    {notification && (
    <div className="notification-memory">
      {notification}
    </div>
  )}
  </div>
);

}

export default ChatPage;