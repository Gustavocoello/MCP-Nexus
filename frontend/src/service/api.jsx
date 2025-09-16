// src/services/api.js
import axios from 'axios';

//const REACT_APP = process.env.REACT_APP_URL; Esto viene del .env
const VITE_APP = import.meta.env.VITE_URL;


// Instancia de axios con configuración básica
const apiClient = axios.create({
  baseURL: VITE_APP,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

export default apiClient;