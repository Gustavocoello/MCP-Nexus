import React, { useEffect, useState } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar/Sidebar';
import ChatPage from './features/chat/ChatPage';
import DashboardPage from './pages/DashboardPage';
import ConfigPage from './features/config/ConfigPage';
import BackgroundTechPattern from './features/config/components/tabs/Theme/BackgroundTechPattern';
import LoginPage from './features/auth/components/LoginPage/LoginPage'; 
import RegisterPage from './features/auth/components/RegisterPage/RegisterPage'; 
import OAuthCallback from './features/auth/utils/McpOauthCallback';
import SpherePage from './pages/SpherePage';
import LandingPage from './pages/LandingPage';
import useCurrentUser from './features/auth/components/context/useCurrentUser';
import './styles/App.css';

function App() {
  const [theme, setTheme] = useState(document.documentElement.getAttribute('data-theme'));
  const { user } = useCurrentUser();

  useEffect(() => {
    const observer = new MutationObserver(() => {
      setTheme(document.documentElement.getAttribute('data-theme'));
    });

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
    return () => observer.disconnect();
  }, []);

  return (
    <div className="app-container">
      {theme === 'custom' && <BackgroundTechPattern />}
      <Sidebar />
      <div className="main-content">
        <Routes>
          {/* LandingPage */}
          <Route path="/" element={<LandingPage />} />

          {/* Chat para invitados */}
          <Route path="/chat" element={<ChatPage guest />} />
          
          {/* Chat para usuarios autenticados */}
            <Route path="/c/:userId" element={<ChatPage />}>
              <Route path="config" element={<ConfigPage />} />
            </Route>

          {/* Otras rutas */}
          <Route path="/oauth-callback" element={<OAuthCallback />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/jarvis" element={<SpherePage />} />
        </Routes>
      </div>
    </div>
  );
}

export default App;
