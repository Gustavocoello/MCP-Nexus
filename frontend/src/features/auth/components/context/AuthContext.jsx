// features/auth/components/context/AuthContext.js
import React, { createContext, useState, useEffect } from 'react';
import { getCurrentUser } from '../authService';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    // Cargar usuario desde localStorage si existe
    const storedUser = localStorage.getItem('auth_user');
    return storedUser ? JSON.parse(storedUser) : null;
  });
  
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchUser = async () => {
      if (user) {
        // Ya hay un usuario en localStorage, no hagas llamada al backend
        setLoading(false);
        return;
      }

       try {
        const currentUser = await getCurrentUser();
        if (currentUser) {
          setUser(currentUser);
          localStorage.setItem('auth_user', JSON.stringify(currentUser));
        }
      } catch (error) {
        console.error("Error obteniendo usuario:", error);
        setUser(null);
        localStorage.removeItem('auth_user');
      } finally {
        setLoading(false);
      }
    };

    fetchUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); 

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
