// src/pages/ChatPage/ChatPage.jsx
import React from 'react';
import { Routes, Route, useLocation, useParams } from 'react-router-dom';
import { JarvisProvider, Sidebar, ChatContainer, ConfigPage } from 'jarvis-sdk-core';
import { useAuthContext } from '@/core/auth/AuthContext';

const ChatPage = () => {
  const { getToken } = useAuthContext();
  const location = useLocation();
  const { userId } = useParams();
  const showSettings = location.pathname.endsWith('/settings');

  return (
    <JarvisProvider 
      config={{ 
        getToken, 
        baseURL: import.meta.env.VITE_URL,
        appId: 'sdk-jarvis-portafolio', // <--- Identificador para tu DB
        theme: 'dark'
      }}
    >
      <div className="sdk-layout-wrapper" style={{ display: 'flex', height: '100vh', width: '100vw' }}>
        {/* El Sidebar vive AQUÍ, por eso solo aparece en el chat */}
        <Sidebar /> 
          {/* EL CHAT SIEMPRE ESTÁ AQUÍ - NUNCA SE DESMONTA */}
          <div className="chat-layer" style={{ 
            flex: 1, 
            width: '100%', 
            height: '100%',
            opacity: showSettings ? 0.4 : 1, // Se oscurece un poco pero NO desaparece
            pointerEvents: showSettings ? 'none' : 'auto', // Evita clicks en el chat si config está abierto
            transition: 'opacity 0.3s ease' 
          }}>
            {/* Si hay userId en la URL, cargamos ese chat, si no, el de invitado */}
            <ChatContainer guest={!userId} />
          </div>

          {/* EL CONFIG ES UN OVERLAY QUE "FLOTA" ENCIMA */}
          {showSettings && (
            <div className="config-overlay" style={{
              position: 'absolute',
              top: 0, 
              right: 0, // Puedes hacerlo lateral o que cubra todo
              width: '100%', 
              height: '100%',
              zIndex: 1000,
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              backdropFilter: 'blur(4px)', // Le da un efecto pro sin quitar el texto de atrás
            }}>
              <ConfigPage />
            </div>
          )}
      </div>
    </JarvisProvider>
  );
};

export default ChatPage;