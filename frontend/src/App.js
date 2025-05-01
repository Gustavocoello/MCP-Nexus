import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import SearchBar from './components/searchBarPrompt';
import Sidebar from './components/Sidebar';

function App() {
  return (
    <Router>
      <div className="app-container">
        {/* Eliminamos el viejo nav y usamos el Sidebar */}
        <Sidebar />
        
        {/* Contenido principal que cambiará con las rutas */}
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

// Componentes de página (mejor moverlos a archivos separados)
function ChatPage() {
  return (
    <div className="page">
      <h1>Chat Interface</h1>
      <SearchBar />
    </div>
  );
}

function DashboardPage() {
  return (
    <div className="page">
      <h1>Dashboard</h1>
      <p>This is the dashboard page (under development)</p>
    </div>
  );
}

function ConfigPage() {
  return (
    <div className="page">
      <h1>Configuration</h1>
      <p>Configuration page for developers (under development)</p>
    </div>
  );
}

export default App;