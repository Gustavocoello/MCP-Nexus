// src/shared/utils/storageAdapter.js (o la ruta donde lo tengas)

export const USER_ID_KEY = 'jarvis_db_user_id';
export const ACTIVE_CHAT_KEY = 'jarvis_active_chat_id';

export const storageAdapter = {
  // Obtener valor (por defecto busca el chat activo si no pasas llave)
  getItem: (key = ACTIVE_CHAT_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem(key);
    }
    return null;
  },

  // Guardar valor
  setItem: (value, key = ACTIVE_CHAT_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      if (value === null || value === undefined) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, value);
      }
    }
  },

  // Eliminar una llave específica
  removeItem: (key = ACTIVE_CHAT_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(key);
    }
  },

  // Limpieza total (Útil para el Logout)
  clearAuthData: () => {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(USER_ID_KEY);
      localStorage.removeItem(ACTIVE_CHAT_KEY);
      // NO borres el token de aquí, Clerk se encarga de su propia sesión
    }
  }
};