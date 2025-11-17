import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Sidebar from '@/components/layout/Sidebar/Sidebar';
import ChatPage from '@/features/chat/ChatPage';
import ConfigPage from '@/features/config/ConfigPage';
import BackgroundTechPattern from '@/features/config/components/tabs/Theme/BackgroundTechPattern';
import LoginPage from '@/features/auth/components/LoginPage/LoginPage'; 
import RegisterPage from '@/features/auth/components/RegisterPage/RegisterPage'; 
import OAuthCallback from '@/features/auth/utils/McpOauthCallback';
import useCurrentUser from '@/features/auth/components/context/useCurrentUser';
import DashboardPage from '@/pages/DashboardPage';
import LandingPage from '@/pages/Landing/LandingPage';
import SpherePage from '@/pages/SpherePage';
import PrivacyPage from '@/pages/Legal/PrivacyPage';
import GuidesPage from '@/pages/Resources/GuidesPage';
import {inject} from '@vercel/analytics';
import '@/styles/App.css';

// Inicializar Vercel Analytics 
inject({ mode: import.meta.env.DEV ? 'development' : 'production' })

function App() {
  const [theme, setTheme] = useState(document.documentElement.getAttribute('data-theme'));
  const location = useLocation();

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.getAttribute('data-theme'));
    });

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  // Rutas exactas que deben ocultar sidebar
  const hideExact = [
    '/',
    '/jarvis',
    '/login',
    '/register',
    '/oauth-callback',
    '/privacy',
  ];

  // Rutas que funcionan como prefijo
  const hidePrefix = [
    '/docs',
    '/api',
    '/guides',
    '/overview',
    '/mission',
    '/contact',
    '/terms',
    '/data'
  ];

  const path = location.pathname;

  // Detectar si coincide con exactas
  const hideByExact = hideExact.includes(path);

  // Detectar si coincide con prefijo real (pero no colisionar con /c/xxx)
  const hideByPrefix = hidePrefix.some(route => path.startsWith(route));

  const hideSidebar = hideByExact || hideByPrefix;

  const shouldLoadUser = !hideSidebar;
  const { user: currentUser } = useCurrentUser();
  const user = hideSidebar ? null : currentUser;


  return (
    <div className="app-container">
      {theme === 'custom' && <BackgroundTechPattern />}
      {!hideSidebar && <Sidebar />}
      <Routes>
      {/* Landing fuera del main-content */}
      <Route path="/" element={<LandingPage />} />

      <Route
        path="*"
        element={
          <div className="main-content">
            <Routes>
              {/* Chat invitados */}
              <Route path="/chat" element={<ChatPage guest />} />

              {/* Chat usuarios */}
              <Route path="/c/:userId" element={<ChatPage />}>
                <Route path="config" element={<ConfigPage />} />
              </Route>

              {/* Otras rutas */}
              <Route path="/oauth-callback" element={<OAuthCallback />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/jarvis" element={<SpherePage />} />
              <Route path="/privacy" element={<PrivacyPage />} />
              {/*<Route path="/terms" element={<TermsPage />} />
              <Route path="/data" element={<DataPracticesPage />} />
              <Route path="/overview" element={<OverviewPage />} />
              <Route path="/mission" element={<MissionPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/docs" element={<DocsPage />} />
              <Route path="/api" element={<ApiPage />} /> */}
              <Route path="/guides" element={<GuidesPage />} />

            </Routes>
          </div>
        }
      />
    </Routes>
  </div>
);

}

export default App;
