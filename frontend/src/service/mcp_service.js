// src/service/mcp_service.js
import { useState } from 'react';
import { useMcp } from 'use-mcp/react';

const MCP_URL = process.env.REACT_APP_MCP_URL;

export function useMcpClient() {
  const [enabled, setEnabled] = useState(false);

  // Hook MCP "apagado" hasta que lo habilitamos
  const mcp = useMcp({
    url: MCP_URL,
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
