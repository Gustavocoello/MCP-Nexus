// src/service/mcp_service.js
import { useState } from 'react';
import { useMcp } from 'use-mcp/react';

//const MCP_URL = process.env.REACT_APP_MCP_URL;
// VITE
const VITE_APP = import.meta.env.VITE_MCP_URL;


export function useMcpClient() {
  const [enabled, setEnabled] = useState(false);

  // Hook MCP "apagado" hasta que lo habilitamos
  const mcp = useMcp({
    url: VITE_APP,
    clientName: 'mcp-client-google-calendar',
    debug: true,
    autoReconnect: false,
    autoRetry: false,
    preventAutoAuth: true,
    enabled,   // 👈 clave: solo conecta si enabled === true
  });

  // Funciones para disparar manualmente
  const start = () => setEnabled(true);
  const stop = () => setEnabled(false);

  return {
    ...mcp,
    start,
    stop,
  };
}
