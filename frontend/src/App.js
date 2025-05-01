import React from 'react';
import './App.css';
import SearchBar from './components/searchBarPrompt';
import Sidebar from './components/Sidebar';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';

function App() {
  return (
    <Router>
      <nav>
        <Link to="/">Chat</Link>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/config">Configuration</Link>
      </nav>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/config" element={<ConfigPage />} />
      </Routes>
    </Router>
  );
}


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
