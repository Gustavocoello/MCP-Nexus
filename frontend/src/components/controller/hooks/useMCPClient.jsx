// hooks/useMCPClient.js
import { useState, useEffect, useCallback, useRef } from 'react';
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const VITE_APP = import.meta.env.VITE_MCP_URL; 
// quitamos slash al final para consistencia

export const useMCPClient = (userId = null) => {
  const [client, setClient] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [tools, setTools] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [resources, setResources] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const hasTriedConnectRef = useRef(false);  // para que solo intente conectar una vez
  const mountedRef = useRef(true);

  const connect = useCallback(async () => {
    if (hasTriedConnectRef.current) {
      // Ya intentó conectar una vez: no vuelvas a hacerlo
      return;
    }
    hasTriedConnectRef.current = true; // marcamos que ya lo intentamos

    setIsLoading(true);
    setError(null);

    try {
      if (!VITE_APP) throw new Error('VITE_MCP_URL no configurada');

      const transport = new StreamableHTTPClientTransport(new URL(VITE_APP), {
        requestInit: {
          headers: {
            'Content-Type': 'application/json',
            ...(userId ? { 'X-User-ID': userId } : {})
          }
        }
      });

      const mcpClient = new Client({ name: 'calendar-frontend', version: '1.0.0' });

      await mcpClient.connect(transport);

      if (!mountedRef.current) return;

      const listToolsResp = await mcpClient.listTools();
      const listPromptsResp = await mcpClient.listPrompts();
      const listResourcesResp = await mcpClient.listResources();

      if (!mountedRef.current) return;

      setTools(listToolsResp?.tools ?? []);
      setPrompts(listPromptsResp?.prompts ?? []);
      setResources(listResourcesResp?.resources ?? []);

      setClient(mcpClient);
      setIsConnected(true);
      console.log('MCP conectado correctamente', { tools: listToolsResp, prompts: listPromptsResp });
    } catch (err) {
      console.error('Error conectando MCP:', err);
      if (!mountedRef.current) return;
      setError(err?.message || String(err));
      setIsConnected(false);
    } finally {
      if (!mountedRef.current) return;
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    mountedRef.current = true;
    connect(); // intento de conexión al montar

    return () => {
      mountedRef.current = false;
      // opcional: cerrar cliente si quieres
      if (client) {
        client.close().catch(e => console.warn('Error closing MCP client:', e));
      }
    };
  }, [connect]);

  const callTool = useCallback(async (name, args = {}) => {
    if (!client || !isConnected) throw new Error('Cliente MCP no conectado');
    return client.callTool({ name, arguments: args });
  }, [client, isConnected]);

  const reconnect = useCallback(async () => {
    // puedes resetear estados si quieres
    setError(null);
    setIsConnected(false);
    setTools([]);
    setPrompts([]);
    setResources([]);
    // Forzar que el hook pueda volver a intentar conexión
    // Si usas un ref para que solo conecte una vez, resetear ese ref también
    // Supongamos que en tu hook usas hasTriedConnectRef:
    if (typeof hasTriedConnectRef !== 'undefined') {
      hasTriedConnectRef.current = false;
    }
    // ahora llamar connect
    await connect();
  }, [connect, setError, setIsConnected, setTools, setPrompts, setResources]);

  return {
    client,
    isConnected,
    isLoading,
    tools,
    prompts,
    resources,
    error,
    callTool,
    reconnect
  };
};
