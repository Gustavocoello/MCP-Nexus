// src/features/auth/components/context/useCurrentUser.js
import { useContext } from 'react';
import { AuthContext } from './AuthContext';

export default function useCurrentUser() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useCurrentUser debe usarse dentro de AuthProvider');
  }

  return context;
}
