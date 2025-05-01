import React from 'react';
import { Link, useLocation } from 'react-router-dom';  // Importamos useLocation
import { FaHome, FaChartBar, FaCog } from 'react-icons/fa';
import './Sidebar.css';

const Sidebar = () => {
  // Obtenemos la ruta actual para resaltar el ítem activo
  const location = useLocation();

  return (
    <div className="sidebar">
      {/* Ítem Home */}
      <Link 
        to="/" 
        className={`sidebar-item ${location.pathname === '/' ? 'active' : ''}`}
        aria-label="Home"
      >
        <FaHome className="icon" />
        <span className="label">Home</span>
      </Link>

      {/* Ítem Dashboard */}
      <Link 
        to="/dashboard" 
        className={`sidebar-item ${location.pathname === '/dashboard' ? 'active' : ''}`}
        aria-label="Dashboard"
      >
        <FaChartBar className="icon" />
        <span className="label">Dashboard</span>
      </Link>

      {/* Ítem Configuración */}
      <Link 
        to="/config" 
        className={`sidebar-item ${location.pathname === '/config' ? 'active' : ''}`}
        aria-label="Settings"
      >
        <FaCog className="icon" />
        <span className="label">Settings</span>
      </Link>
    </div>
  );
};

export default Sidebar;