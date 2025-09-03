// mcp-scratch/frontend/src/service/useAuthStatus.js
import { useEffect, useState } from 'react';
import axios from 'axios';

//const REACT_APP = process.env.REACT_APP_URL;
// Vite
const VITE_APP = import.meta.env.VITE_URL;


export default function useAuthStatus() {
  const [isAuthenticated, setIsAuthenticated] = useState(null);

  useEffect(() => {
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
          setIsAuthenticated(false); // o null si prefieres marcar error
        }
      });
  }, []);

  return isAuthenticated;
}
