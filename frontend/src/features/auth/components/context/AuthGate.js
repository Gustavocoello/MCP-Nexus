// src/features/auth/components/context/AuthGate.jsx
import React from 'react';
import useCurrentUser from './useCurrentUser';

const AuthGate = ({ children }) => {
  const { loading } = useCurrentUser();

  if (loading) {
    return <div className="auth-loading">Cargando...</div>; // Puedes hacer un spinner aquí
  }

  return children;
};

export default AuthGate;
