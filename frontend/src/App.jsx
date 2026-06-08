// src/App.jsx
import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
// PAGE 
import DashboardPage from '@/projects/dashboard/DashboardPage';
import LandingPage from '@/pages/Landing/LandingPage';
import SpherePage from '@/projects/voice-sphere/SpherePage';
import PrivacyPage from '@/pages/Landing/About/PrivacyPage';
import GuidesPage from '@/pages/Landing/Resources/GuidesPage';
import MissionPage from '@/pages/Landing/About/MissionPage';
import ContactPage from '@/pages/Landing/About/ContactPage';
import TermsPage from '@/pages/Landing/About/TermsPage';
import ClerkLayout from '@/core/auth/layout/ClerkLayout';
// AUTH
import { setAuthToken as setApiServiceAuthToken } from '@/core/api/client';
import { SignIn, SignUp, useUser } from "@clerk/clerk-react";
import { useSyncUser } from '@/core/auth/hook/useSyncUser';
import { useAuthContext } from '@/core/auth/AuthContext';
import { authLogger } from '@/shared/log/logger.jsx';
// SDK
import ChatPage from '@/projects/jarvis-chat/ChatPage';

import {inject} from '@vercel/analytics';
import '@/styles/App.css';

// Inicializar Vercel Analytics 
if (import.meta.env.VITE_DEBUG === 'true') {
  inject({ mode: 'debug' }); // puedes poner lo que quieras
}

function App() {
  const [theme, setTheme] = useState(document.documentElement.getAttribute('data-theme'));
  const { isSignedIn } = useUser();
  const { dbUserId, isSynced, syncError } = useSyncUser();
  const { getToken } = useAuthContext();


  useEffect(() => {
    // Solo configuramos el token si el usuario ya pasó todos los factores (2FA incluido)
    if (isSignedIn && getToken) {
      //setApiAuthToken(getToken);
      setApiServiceAuthToken(getToken);
      authLogger.info('✅ Token configurado globalmente');
      }
  }, [isSignedIn, getToken]);

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.getAttribute('data-theme'));
    });

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  // Opcional: Mostrar error de sincronización si ocurre
  useEffect(() => {
    if (syncError) {
      authLogger.error('Error sincronizando usuario:', syncError);
      // Aquí podrías mostrar un toast o notificación al usuario
    }
  }, [syncError])



  return (
    <div className="app-container">
      <Routes>
        <Route path="/" element={<LandingPage />} />
        {/* TODAS LAS DEMÁS RUTAS VAN DENTRO DE MAIN-CONTENT */}
        <Route path="*" element={
          <div className="main-content">
              <Routes>
                <Route path="/" element={<LandingPage />} />
                  {/* El ChatPage es ahora una "isla" independiente */}
                  <Route path="/chat/*" element={<ChatPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  
                  {/* Auth routes - simplificadas */}
                  <Route path="/login" element={ <ClerkLayout> <SignIn/> </ClerkLayout>} />

                  {/* Páginas públicas */}
                  <Route path="/jarvis" element={<SpherePage />} />
                  <Route path="/privacy" element={<PrivacyPage />} />
                  <Route path="/guides" element={<GuidesPage />} />
                  <Route path="/mission" element={<MissionPage />} />
                  <Route path="/contact" element={<ContactPage />} />
                  <Route path="/terms" element={<TermsPage />} />

                  {/* Rutas comentadas para cuando las necesites
                  <Route path="/data" element={<DataPracticesPage />} />
                  <Route path="/overview" element={<OverviewPage />} />
                  <Route path="/docs" element={<DocsPage />} />
                  <Route path="/api" element={<ApiPage />} />
                  */}
                </Routes>
          </div>
          }/>
        </Routes>
      </div>
  );
}

export default App;



/*
import React from 'react';
import { useUser } from "@clerk/clerk-react";
import { JarvisProvider } from "@sdk/context/JarvisProvider";
import Sidebar from "@sdk/components/Sidebar/Sidebar";
import ChatContainer from "@sdk/components/ChatContainer/ChatContainer";
import { useAuthContext } from "@/context/AuthContext";
// Tu botón personalizado
import LoginButton from '@/components/layout/LoginButton/LoginButton';

const PruebaChatSDK = () => {
  const { isLoaded, isSignedIn } = useUser();
  const { getToken } = useAuthContext();

  // 1. Estado de carga inicial
  if (!isLoaded) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', background: '#0e0e0e' }}>
        <p style={{ color: '#666', fontFamily: 'sans-serif' }}>Inicializando entorno de pruebas...</p>
      </div>
    );
  }

  // 2. Si no hay sesión, mostramos tu LoginButton
  if (!isSignedIn) {
    return (
      <div style={{ 
        display: 'flex', 
        flexDirection: 'column', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh', 
        background: '#0e0e0e',
        gap: '20px'
      }}>
        <h2 style={{ color: 'white', fontFamily: 'sans-serif', fontWeight: '300' }}>
          Jarvis <span style={{ color: '#007bff' }}>SDK</span> Lab
        </h2>
        <LoginButton /> 
        <p style={{ color: '#444', fontSize: '0.8rem' }}>Inicia sesión para vincular tu ID de Agente</p>
      </div>
    );
  }

  // 3. Renderizado del SDK una vez autenticado
  return (
    <JarvisProvider 
      config={{ 
        getToken: getToken,
        baseURL: import.meta.env.VITE_URL,
        theme: 'dark'
      }}
    >
      <div style={{ display: 'flex', width: '100vw', height: '100vh', overflow: 'hidden' }}>
        <Sidebar />
        <main style={{ flex: 1, position: 'relative', background: '#121212' }}>
          <ChatContainer />
        </main>
      </div>
    </JarvisProvider>
  );
};

export default PruebaChatSDK;

*/














