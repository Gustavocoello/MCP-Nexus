// src/services/storageAdapter.js

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
      localStorage.setItem(key, value);
    }
  },
  removeItem: (key = STORAGE_KEY) => {
    if (typeof window !== 'undefined' && window.localStorage) {
      localStorage.removeItem(key);
    }
  }
};