import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Outlet, useLocation, useParams, Navigate, Link } from 'react-router-dom';
import MarkdownIt from 'markdown-it';
import SearchBar from '@/components/ui/SearchBar/SearchBar';
import useChatMessages from '../chat/hooks/useChatMessages';
import MessageList from './components/MessageList/MessageList';
import LoginButton from '@/components/layout/LoginButton/LoginButton';
import { useAuth } from '@clerk/clerk-react';
import { useAuthContext } from '@/features/auth/components/context/AuthContext';
import { TbMessagePlus } from "react-icons/tb";
import { getAllChats, createChat} from '../../service/chatService';
import { sendMessage, sendAnonymousMessage} from '../../service/api_service';
import { hookLogger, streamLogger } from '@/components/controller/log/logger.jsx';

// Cambiando de Markdown a HTML
const md = new MarkdownIt({
  html: false, // Antes True ahora False para no escaparse
  linkify: true,
});

//  Contiene todos componentes efectos de la interfaz de Jarvis
const ChatPage = () => {
  
  // Estados
  const { user, isAuthenticated } = useAuthContext();
  const { isLoaded } = useAuth();
  const loading = !isLoaded;
  const { userId } = useParams(); // Para futuras mejoras multiusuario
  const location = useLocation();
  const [localMessages, setLocalMessages] = useState([]);
  const [isJarvisTyping, setIsJarvisTyping] = useState(false);
  const [hasSentMessage, setHasSentMessage] = useState(false);
  const [activeChatId, setActiveChatId] = useState(null);
  const [abortController, setAbortController] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const chatBottomRef = useRef(null);
  const [notification, setNotification] = useState(null);
  const [pendingContext, setPendingContext] = useState([]);
  const isChatRoute = location.pathname.startsWith('/c/');
  const isConfigOpen = location.pathname.endsWith('/settings');
  const scrollInitialized = useRef(false);

  // ---------------- HOOKS PERSONALIZADOS ----------------  
  // Hook personalizado para manejar mensajes del chat
  const {
    messages: cachedMessages,
    appendMessageToCache,
    updateMessageInCache,
    lastUserMessageId, // <-- Nuevo: para el scroll
    isSuccess,         // <-- Nuevo: para saber cuándo terminó de cargar la RAM
  } = useChatMessages(activeChatId, {
    enabled: isChatRoute && !!activeChatId,
    keep: 10, // Mantener máximo 10 mensajes en la memoria de 3.3GB
  });
  // -------------------- CALLBACKS ---------------------
  // Función para cargar todos los chats del usuario
  const loadAllChats = async () => {
  try {
    const chats = await getAllChats(); // Llama al backend
    return chats;
  } catch (error) {
    streamLogger.error('Error cargando chats:', error);
    return [];
  } 
  };

  // Función para crear nuevo chat
  const createNewChat = async () => {
    try {
      const newChat = await createChat({}); // Backend genera el ID
      setActiveChatId(newChat.id);
      localStorage.setItem('activeChatId', newChat.id);
      setHasSentMessage(false);

      // Ya no seteamos setMessages([]) porque el hook cargará vacío

      window.dispatchEvent(new CustomEvent('chats-updated', {
        detail: { newChatId: newChat.id }
      }));

    } catch (error) {
      streamLogger.error('Error creando chat:', error);
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

  // ==========  Función para manejar nuevos mensajes ===========
  const handleNewMessage = useCallback(async (message, contextFromFile = '', image = null, tool = '') => {
  if (message.role !== 'user') return;
   
  const controller = new AbortController();
  setAbortController(controller);
  setIsStreaming(true);
  const userContent = message.content ?? message.text ?? '';
  const jarvisTempId = `jarvis-${Date.now()}`;
  
  const combinedContext = Array.isArray(contextFromFile)
  ? contextFromFile.map(c => `🗂️ ${c.name}:\n${c.text}`).join('\n\n')
  : contextFromFile;

  streamLogger.info("🔧 Tool seleccionada:", tool); // hay que eliminar

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
  const timestamp = Date.now();
  const htmlParts = [];

  const currentImage = image

  if (currentImage) {
    htmlParts.push(`<img src="${currentImage}" class="chat-image-upload" />`);
  }

 if (userContent) {
   htmlParts.push(`<p>${escapeHtml(userContent)}</p>`);
 }

 const combinedHtml = htmlParts.join('<br><br>');

 const newMessages = [];

 if (htmlParts.length > 0) {
   newMessages.push({
     id: `user-${timestamp}`,
     role: 'user',
     type: 'html',
     content: userContent,
     html: combinedHtml,
   });
 }

 newMessages.push({
   id: jarvisTempId,
   role: 'assistant',
   content: '',
   html: '',
   stable: false, // Indica que está en proceso
 });

  appendMessageToCache(newMessages);
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
        updateMessageInCache(jarvisTempId, { content: fullReply, stable: true });
        showNotification("Has alcanzado el límite de mensajes gratuitos. Inicia sesión para continuar.");
        setIsJarvisTyping(false);
        setIsStreaming(false);
        return;
      }

      // ✅ Solo se hace la solicitud si no ha alcanzado el límite
      res = await sendAnonymousMessage(fullPrompt);

      // Incrementar contador después de la respuesta
      localStorage.setItem('anonMessageCount', String(anonCount + 1));
      streamLogger.info('Mensajes de usuarios no registrados:', anonCount );

      if (res.result) {
        fullReply = res.result;
      } else if (res.error) {
        fullReply = res.error;
      }

      updateMessageInCache(jarvisTempId, { content: fullReply, stable: true });
    // Mensajes para usuarios logeados
    } else {
      res = await sendMessage({
        chatId: activeChatId,
        text: userContent,
        hidden_context: combinedContext,
        tool: tool
      }, (partial) => {
        // streaming parcial para usuarios logueados
        streamLogger.info('partial recibido:', partial);
        

        let cleanPartial = partial;

        if (partial.includes('[NOTIFICATION]')) {
          const parts = partial.split('[NOTIFICATION]');
          cleanPartial = parts[0].trim();
          const notificationText = parts[1]?.trim();
          if (notificationText) {
            showNotification(notificationText);
          }
        }

        updateMessageInCache(jarvisTempId, {
          id: jarvisTempId,
          role: 'assistant',
          content: cleanPartial,
          html: md.render(cleanPartial),
          stable: false // Sigue en proceso
        });
        
      }, controller.signal);
      updateMessageInCache(jarvisTempId, { stable: true });
    }
  } catch (err) {
    if (err.name !== 'AbortError') {
      streamLogger.error(err);
      updateMessageInCache(jarvisTempId, { 
      stable: true, 
      html: '<p style="color: red;">Error al procesar la solicitud.</p>' 
    });
    }

  } finally {
    setIsJarvisTyping(false);
    setIsStreaming(false);
    setAbortController(null);
    setPendingContext([]);
    updateMessageInCache(jarvisTempId, (prev) => ({ ...prev, stable: true })); 
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
  
  // ------------------- EFECTOS --------------------------

  // Efecto para saltar a la última pregunta (Anclaje)
  useEffect(() => {
    if (isSuccess && lastUserMessageId && !scrollInitialized.current) {
      const timer = setTimeout(() => {
        const element = document.getElementById(`msg-${lastUserMessageId}`);
        if (element) {
          streamLogger.info(`[Anclaje] Saltando a la última pregunta: ${lastUserMessageId}`);
          element.scrollIntoView({ behavior: 'auto', block: 'start' });
          scrollInitialized.current = true;
        }
      }, 150); // Pequeño margen para que el HTML se renderice
      return () => clearTimeout(timer);
    }
  }, [isSuccess, lastUserMessageId, activeChatId]);

  // Resetear el ancla si cambias de chat
  useEffect(() => {
    scrollInitialized.current = false;
  }, [activeChatId]);

  // Efecto: Sincronizar mensajes cacheados con mensajes locales
  useEffect(() => {
    const formatted = cachedMessages.map(m => {
      if (m.role === 'assistant') {
        return { ...m, html: md.render(m.content || '') };
      } else {
        const userHtml = (m.content || '')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;');
        return { ...m, html: `<p>${userHtml}</p>` };
      }
    });
    setLocalMessages(formatted);
  }, [cachedMessages]);


  // Efecto: Inicializar chat activo, solo seteamos activeChatId, NO mensajes
  useEffect(() => {
    const initChat = async () => {
      const allChats = await loadAllChats();
      if (allChats.length === 0) return;

      const savedChatId = localStorage.getItem('activeChatId');
      let chatToLoad = allChats.find(chat => chat.id === savedChatId);

      if (!chatToLoad) {
        chatToLoad = allChats[0]; // fallback: primer chat si no se encontró el guardado
      }

      // Eliminamos la carga manual de mensajes y el setMessages
      setActiveChatId(chatToLoad.id);
      localStorage.setItem('activeChatId', chatToLoad.id);
    };

    initChat();
  }, []);

  // Efecto para escuchar eventos de carga chat, solo setActiveChatId
  // 1. Un solo lugar para reaccionar al cambio de chat
  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem('activeChatId', activeChatId);
      // Al cambiar el activeChatId, el hook useChatMessages 
      // automáticamente detectará el cambio y traerá los mensajes nuevos.
    }
  }, [activeChatId]);
  
  // 2. Escuchar al sidebar de forma limpia
  useEffect(() => {
    const handleChatLoaded = (event) => {
      const { chatId } = event.detail;
      if (chatId !== activeChatId) {
        setActiveChatId(chatId);
      }
    };
    window.addEventListener('chat-loaded', handleChatLoaded);
    return () => window.removeEventListener('chat-loaded', handleChatLoaded);
  }, [activeChatId]);

  // Cada vez que cambia el chat activo, actualiza localStorage
  useEffect(() => {
    if (activeChatId) {
      localStorage.setItem('activeChatId', activeChatId);
    }
  }, [activeChatId]);

  // Efecto: Limpiar contador de mensajes anónimos al autenticarse
  useEffect(() => {
    if (isAuthenticated === true) {
      localStorage.removeItem('anonMessageCount');
    }
  }, [isAuthenticated]);
  
  if (loading) {
    streamLogger.info('Usuario actual:', user);
    return <div className="loading-screen">Cargando usuario...</div>;
  
  }
  // Efecto: Vigilar cambios en la RAM y actualizar mensajes locales
  // ChatPage.jsx - Efecto de Sincronización Corregido
  useEffect(() => {
    if (!cachedMessages || cachedMessages.length === 0) return;
  
    const formatted = cachedMessages.map(m => {
      const isAssistant = m.role === 'assistant';
      
      // Si es asistente y NO tiene contenido aún (está empezando)
      if (isAssistant && !m.content && !m.html) {
        return { ...m, html: '<span class="typing-dots">...</span>', stable: false };
      }
  
      // GENERAR HTML SIEMPRE QUE NO EXISTA
      // Esto asegura que si viene null del backend (como en tu JSON), se genere ahora
      let generatedHtml = m.html;
  
      if (!generatedHtml) {
        if (isAssistant) {
          generatedHtml = md.render(m.content || '');
        } else {
          // Escapado de seguridad para mensajes del usuario
          const safeContent = (m.content || '')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>');
          generatedHtml = `<p>${safeContent}</p>`;
        }
      }
  
      return {
        ...m,
        html: generatedHtml,
        stable: m.stable !== undefined ? m.stable : true
      };
    });
  
    streamLogger.info("Sincronizando mensajes locales con HTML generado");
    setLocalMessages(formatted);
  
    // Control del indicador de escritura
    const lastMsg = formatted[formatted.length - 1];
    if (lastMsg && lastMsg.role === 'assistant' && lastMsg.stable === false) {
      setIsJarvisTyping(true);
      setIsStreaming(true);
    } else if (!isStreaming) {
      setIsJarvisTyping(false);
    }
  }, [cachedMessages, isStreaming]);
  
  // Efecto: Loguear estado del chat en cada cambio de mensajes
  useEffect(() => {
    if (localMessages.length > 0) {
      streamLogger.group('📊 ESTADO DEL CHAT', () => {
        streamLogger.info('Chat ID:', activeChatId);
        streamLogger.info('Total en pantalla:', localMessages.length);
        streamLogger.info('Total en caché:', cachedMessages?.length || 0);
        
        // Ver últimos 3 mensajes
        const last3 = localMessages.slice(-3).map(m => ({
          id: m.id,
          role: m.role,
          preview: (m.content || '').substring(0, 30) + '...'
        }));
        streamLogger.table(last3);
      });
    }
  }, [activeChatId, localMessages.length]);

  
  // Protección de ruta: si no está autenticado y está en /c/:userId → redirigir a login
    if (!loading && !isAuthenticated && location.pathname.startsWith('/c/')) {
     return <Navigate to="/login" replace />;
   }


  return (
  <div className="page">
    {/* Aquí va el botón para iniciar sesion si No esta autenticado*/}
    {!isAuthenticated && <LoginButton />} 

    {/* Botón de nuevo chat */}
    {isAuthenticated && (
    <button className="new-chat-button" onClick={createNewChat}>
      <TbMessagePlus size={23} />
    </button>
    )}

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
      <MessageList messages={localMessages || []} />
      <div ref={chatBottomRef}/>  {/*DIV vacío para controlar el scroll */ }

      {/* Indicador de escritura */}
      {isJarvisTyping && (
        <div className="typing-indicator">Jarvis está escribiendo...</div>
      )}
    </div>

    {/* Barra de búsqueda / entrada */}
    <SearchBar 
      onSearch={(userQuery, context, image, tool) => handleNewMessage({ role: 'user', text: userQuery }, context, image, tool)}
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
    {/* Modal de config si está en /config */}
      {user?.id && (
        <Link to={`/c/${user.id}/config`} className="config-modal"></Link>
      )}
    <Outlet />
  </div>
);

}

export default ChatPage;