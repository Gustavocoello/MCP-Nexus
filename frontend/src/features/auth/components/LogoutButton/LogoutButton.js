import React from 'react';
import { useNavigate } from 'react-router-dom';
import { logoutUser } from '../../../auth/components/authService';
import useCurrentUser from '../context/useCurrentUser';
import './LogoutButton.css';

const LogoutButton = () => {
  const navigate = useNavigate();
  const { logout } = useCurrentUser();

  const handleLogout = async () => {
    try {
      await logoutUser();
      logout();
      navigate('/login');
    } catch (error) {
      console.error('Error al cerrar sesión:', error);
    }
  };

  return (
    <div className="logout-button" onClick={handleLogout}>
      Cerrar sesión
    </div>
  );
};

export default LogoutButton;
