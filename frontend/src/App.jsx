import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import Sidebar from '@/components/layout/Sidebar/Sidebar';
import ChatPage from '@/features/chat/ChatPage';
import ConfigPage from '@/features/config/ConfigPage';
import BackgroundTechPattern from '@/features/config/components/tabs/Theme/BackgroundTechPattern';
import DashboardPage from '@/pages/DashboardPage';
import LandingPage from '@/pages/Landing/LandingPage';
import SpherePage from '@/pages/SpherePage';
import PrivacyPage from '@/pages/Legal/PrivacyPage';
import GuidesPage from '@/pages/Resources/GuidesPage';
import MissionPage from '@/pages/About/MissionPage';
import ContactPage from '@/pages/About/ContactPage';
import TermsPage from '@/pages/Legal/TermsPage';
import ClerkLayout from '@/components/layout/Clerk/ClerkLayout';
import {inject} from '@vercel/analytics';
import { SignIn, SignUp, useUser } from "@clerk/clerk-react";
import { useSyncUser } from '@/features/auth/hook/useSyncUser';
import { useAuthContext } from '@/features/auth/components/context/AuthContext';
import { setAuthToken as setApiServiceAuthToken } from '@/service/api'; 
import { authLogger } from '@/components/controller/log/logger.jsx';
import Logger from '@/components/controller/log/logger.jsx';
import '@/styles/App.css';

// Inicializar Vercel Analytics 
if (import.meta.env.VITE_DEBUG === 'true') {
  inject({ mode: 'debug' }); // puedes poner lo que quieras
}

function App() {
  const [theme, setTheme] = useState(document.documentElement.getAttribute('data-theme'));
  const location = useLocation();
  const { isSignedIn } = useUser();
  const { dbUserId, isSynced, syncError } = useSyncUser();
  const { getToken } = useAuthContext();
  const navigate = useNavigate();

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

  // Determinar si mostrar sidebar basado en la ruta actual
  const showSidebar = () => {
    const { pathname } = location; // Extraemos pathname directamente de location
    return (
      pathname === '/dashboard' || 
      pathname.startsWith('/chat/')
    );
  };

  const handleAuthRequired = () => {
    authLogger.warn('Acción de chat requiere autenticación, redirigiendo...');
    navigate('/login');
  };

  return (
    <div className="app-container">
      {theme === 'custom' && <BackgroundTechPattern />}
      
      {/* Sidebar solo en chat y dashboard */}
      {showSidebar() && <Sidebar />}
      
      <Routes>
        {/* Landing sin main-content */}
        <Route path="/" element={<LandingPage />} />

        {/* Rutas con main-content */}
        <Route
          path="*"
          element={
            <div className="main-content">
              <Routes>
                {/* Chat invitados */}
                <Route path="/chat" element={
                  isSignedIn && isSynced
                    ? <Navigate to={`/chat/${dbUserId}`} replace /> 
                    : <ChatPage guest onUnauthorized={handleAuthRequired}/> 
                } />

                {/* Chat usuarios */}
                <Route 
                  path="/chat/:userId" 
                  element={
                    isSignedIn && isSynced
                    ? <ChatPage onUnauthorized={handleAuthRequired}/>
                    : isSignedIn
                      ? <div className="loading-screen">Sincronizando con Jarvis...</div>
                      : <SignIn redirectUrl={location.pathname} />} 
                >
                  <Route 
                    path="settings" 
                    element={<ConfigPage />} 
                  />
                </Route>

                {/* Dashboard */}
                <Route
                  path="/dashboard"
                  element={
                    isSignedIn && isSynced
                    ? <DashboardPage /> 
                    : isSignedIn
                      ? <div className="loading-screen">Sincronizando con Jarvis...</div>
                      : <SignIn redirectUrl="/dashboard" />}
                />
                
                {/* Auth routes - simplificadas */}
                <Route 
                  path="/login" 
                  element={
                    <ClerkLayout>
                      <SignIn/>
                    </ClerkLayout>
                  } 
                />

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
          }
        />
      </Routes>
    </div>
  );
}

export default App;