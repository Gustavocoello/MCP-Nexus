// authService.js 
import { useUser, useAuth } from "@clerk/clerk-react";
import { authLogger } from '@/components/controller/log/logger.jsx';



export function useConnectGoogleCalendar() {
  const { user } = useUser();
  const { getToken } = useAuth();
  const VITE_APP = import.meta.env.VITE_URL;
  const API_BASE = `${VITE_APP}/api/v1`;

  const connectGoogle = async () => {
    if (!user) {
      authLogger.error("No user logged in from Clerk");
      // Retorna false o lanza un error si el usuario no está
      throw new Error("User not logged in."); 
    }

    try {
      // 1. Obtener el token de autenticación y llamar al backend para iniciar OAuth
       const token = await getToken({ template: 'backend-api-jarvis' });
      
      if (!token) {
        throw new Error("Failed to get authentication token");
      }
      
      // 2. Obtener URL desde tu backend CON TOKEN
      const res = await fetch(`${API_BASE}/auth/google/login`, {
        headers: {
          'Authorization': `Bearer ${token}`, 
          'Content-Type': 'application/json'
        }
      });
      
      if (!res.ok) {
        throw new Error(`Backend fetch failed with status: ${res.status}`);
      }
      
      const data = await res.json();  
       
      const authUrl = data.auth_url;

      if (!authUrl) {
          throw new Error("Auth URL not received from backend.");
      }

      // 2. Construir redirect con userId para el backend
      const finalUrl = `${authUrl}&userId=${user.id}`;

      // 3. Redirigir a Google OAuth
      window.location.href = finalUrl;
      
      // La redirección detiene el flujo, no necesitamos retornar true/false aquí.

    } catch (error) {
      authLogger.error("Google OAuth error:", error);
      throw error; // Propagar el error para que el componente que llama lo maneje
    }
  };
  
  return connectGoogle;
}
