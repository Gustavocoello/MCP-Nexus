// src/features/auth/components/context/AuthGate.jsx
import React from 'react';
import { useAuth } from '@clerk/clerk-react';

export default function AuthGate({ children }) {
  const { isLoaded } = useAuth();

  if (!isLoaded) {
    return <div className="auth-loading">Cargando...</div>;
  }

  return children;
}

