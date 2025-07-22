import React, { createContext, useState, useEffect } from 'react';
import { getCurrentUser } from '../authService';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    // Cargar usuario desde localStorage si existe
    const storedUser = localStorage.getItem('auth_user');
    return storedUser ? JSON.parse(storedUser) : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUser = async () => {
      if (user) {
        // Ya hay un usuario en localStorage, no hagas llamada al backend
        setLoading(false);
        return;
      }

      try {
        const currentUser = await getCurrentUser();
        setUser(currentUser);
        localStorage.setItem('auth_user', JSON.stringify(currentUser));
      } catch (error) {
        setUser(null);
        localStorage.removeItem('auth_user');
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
  }, [user]);

  const logout = () => {
    setUser(null);
    localStorage.removeItem('auth_user');
    // Aquí también podrías llamar a un `logout` en el backend
  };

  return (
    <AuthContext.Provider value={{ user, setUser, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
