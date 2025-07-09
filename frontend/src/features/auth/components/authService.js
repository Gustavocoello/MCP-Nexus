// src/service/authService.js
import axios from 'axios';

const API_BASE = process.env.REACT_APP_URL || '';
const AUTH_BASE = `${API_BASE}/api/v1/auth`;

// ------------------- LOGIN -------------------
export const loginUser = async (email, password) => {
  const res = await axios.post(`${AUTH_BASE}/login`, { email, password }, {
    withCredentials: true
  });
  return res.data;
};

// ----------------- GET CURRENT USER -----------------
export const getCurrentUser = async () => {
  const res = await axios.get(`${AUTH_BASE}/me`, {
    withCredentials: true
  });
  return res.data;
};

// ----------------- LOGOUT -----------------
export const logoutUser = async () => {
  const res = await axios.post(`${AUTH_BASE}/logout`, {}, {
    withCredentials: true
  });
  return res.data;
};


// ----------------- REGISTER -----------------
export const registerUser = async ({ name, email, password }) => {
  const res = await axios.post(`${AUTH_BASE}/register`, { name, email, password }, {
    withCredentials: true
  });
  return res.data;
};
// ----------------- GOOGLE LOGIN REDIRECT -----------------
export const loginWithGoogle = () => {
  window.location.href = `${AUTH_BASE}/google/login`;
};

// ----------------- GITHUB LOGIN REDIRECT -----------------
export const loginWithGitHub = () => {
  window.location.href = `${AUTH_BASE}/github/login`;
};
