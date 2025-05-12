import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaChartBar, FaCog } from 'react-icons/fa';
import AnimatedJarvis from './AnimatedJarvis';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();

  return (
    <div className="sidebar">
      {/* Contenedor para ítems superiores */}
      <div className="sidebar-upper">
        <Link 
          to="/" 
          className={`sidebar-item jarvis ${location.pathname === '/' ? 'active' : ''}`}>
        <div className="jarvis-logo">
          <AnimatedJarvis />
        </div>
        </Link>

        <Link 
          to="/dashboard" 
          className={`sidebar-item ${location.pathname === '/dashboard' ? 'active' : ''}`}
        >
          <FaChartBar className="icon" />
          <span className="label">Dashboard</span>
        </Link>
      </div>

      {/* Ítem Settings (sin contenedor inferior) */}
      <Link 
        to="/config" 
        className={`sidebar-item ${location.pathname === '/config' ? 'active' : ''}`}
      >
        <FaCog className="icon" />
        <span className="label">Settings</span>
      </Link>
    </div>
  );
};

export default Sidebar;