import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/layout/Sidebar/Sidebar';
import ChatPage from './features/chat/ChatPage';
import DashboardPage from './pages/DashboardPage';
import ConfigPage from './features/config/ConfigPage';
import BackgroundTechPattern from './features/config/components/tabs/Theme/BackgroundTechPattern';
import LoginPage from './features/auth/components/LoginPage/LoginPage'; 
import RegisterPage from './features/auth/components/RegisterPage/RegisterPage'; 
import './styles/App.css';

function App() {
  const [theme, setTheme] = useState(document.documentElement.getAttribute('data-theme'));

  useEffect(() => {
    const observer = new MutationObserver(() => {
      const newTheme = document.documentElement.getAttribute('data-theme');
      setTheme(newTheme);
    });

    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    return () => observer.disconnect();
  }, []);

  return (
    <Router>
      <div className="app-container">
        {theme === 'custom' && <BackgroundTechPattern />}
        <Sidebar />
        <div className="main-content">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/config" element={<ConfigPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
