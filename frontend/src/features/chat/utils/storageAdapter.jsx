// src/features/chat/utils/storageAdapter.jsx

export const USER_ID_KEY = 'db_user_id';
const STORAGE_KEY = 'activeChatId';

export const storageAdapter = {
  getItem: (key = STORAGE_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      return localStorage.getItem(key);
    }
    return null;
  },
  setItem: (value, key = STORAGE_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      // 🛡️ Evitamos guardar undefined o nulls accidentales como string "null"
      if (value === null || value === undefined) {
        localStorage.removeItem(key);
      } else {
        localStorage.setItem(key, value);
      }
    }
  },
  removeItem: (key = STORAGE_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(key);
    }
  }
};