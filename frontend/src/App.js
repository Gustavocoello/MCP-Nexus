import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import ConfigPage from './pages/ConfigPage';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Sidebar />

        {/* Contenido principal */}
        <div className="main-content">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/config" element={<ConfigPage />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;