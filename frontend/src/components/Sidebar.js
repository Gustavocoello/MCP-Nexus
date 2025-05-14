import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FaChartBar, FaCog, FaBars } from 'react-icons/fa';
import AnimatedJarvis from './AnimatedJarvis';
import './Sidebar.css';

const Sidebar = () => {
  const location = useLocation();
  const [isOpen, setIsOpen] = useState(true); // true = abierto por defecto

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      {/* Botón de toggle */}
      <div className="sidebar-toggle" onClick={() => setIsOpen(!isOpen)}>
        <FaBars size={20} />
      </div>

      {/* Logo Jarvis */}
      <div className="sidebar-upper">
        <Link 
          to="/" 
          className={`sidebar-item jarvis ${location.pathname === '/' ? 'active' : ''}`}
        >
          <div className="jarvis-logo">
            <AnimatedJarvis />
          </div>
        </Link>

        {/* Dashboard */}
        <Link 
          to="/dashboard" 
          className={`sidebar-item ${location.pathname === '/dashboard' ? 'active' : ''}`}
        >
          <FaChartBar className="icon" />
          <span className="label">Dashboard</span>
        </Link>
      </div>

      {/* Settings */}
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