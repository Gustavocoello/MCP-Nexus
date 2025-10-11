// src/service/useAuthStatus.js
import { useEffect, useState } from 'react';
import axios from 'axios';
import { useLocation } from 'react-router-dom';

const VITE_APP = import.meta.env.VITE_URL;

export default function useAuthStatus() {
  const [isAuthenticated, setIsAuthenticated] = useState(null);
  const location = useLocation();

  // Rutas donde NO necesitamos verificar autenticación
  const publicRoutes = ['/', '/login', '/register', '/oauth-callback'];
  const isPublicRoute = publicRoutes.includes(location.pathname);

  useEffect(() => {
    // 🚫 Si es ruta pública, no verifiques nada
    if (isPublicRoute) {
      setIsAuthenticated(false); // o null, como prefieras
      return;
    }

    const url = `${VITE_APP}/api/v1/auth/me`;
    console.log('[useAuthStatus] Verificando autenticación en:', url);

    axios.get(url, { withCredentials: true })
      .then(res => {
        console.log('[useAuthStatus] Usuario autenticado:', res.data);
        setIsAuthenticated(!!res.data?.id);
      })
      .catch(err => {
        if (err.response?.status === 401) {
          console.log('[useAuthStatus] Usuario no autenticado (401)');
          setIsAuthenticated(false);
        } else {
          console.error('[useAuthStatus] Error en la verificación:', err);
          setIsAuthenticated(false);
        }
      });
  }, [location.pathname]);

  return isAuthenticated;
}
