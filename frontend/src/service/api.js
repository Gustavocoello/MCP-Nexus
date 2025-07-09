// src/services/api.js
import axios from 'axios';

const REACT_APP = process.env.REACT_APP_URL; // Esto viene del .env

// Instancia de axios con configuración básica
const apiClient = axios.create({
  baseURL: REACT_APP,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

export default apiClient;