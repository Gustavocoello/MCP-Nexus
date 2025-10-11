import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuthStatus from '@/service/useAuthStatus';
import './LoginButton.css';

const LoginButton = () => {
  const isAuthenticated = useAuthStatus();
  const [show, setShow] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const handleSidebarToggle = (e) => {
      const isSidebarOpen = e.detail?.isOpen;
      setShow(!isSidebarOpen); // Mostrar solo si está cerrado
    };

    window.addEventListener('sidebar-toggled', handleSidebarToggle);
    return () => window.removeEventListener('sidebar-toggled', handleSidebarToggle);
  }, []);

  if (isAuthenticated || !show) return null;

  return (
    <button 
    className={`login-button ${!show ? 'hidden' : ''}`}
    onClick={() => navigate('/login')}>
      Iniciar Sesión
    </button>
  );
};

export default LoginButton;
