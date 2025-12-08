// hooks/useMCPTools.js
import { useState, useEffect, useCallback } from 'react';
import { mcpLogger, apiLogger } from '@/components/controller/log/logger.jsx';

const JARVIS_API = import.meta.env.VITE_URL;

export const useMCPTools = () => {
  const [tools, setTools] = useState([]);
  const [prompts, setPrompts] = useState([]);
  const [resources, setResources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  const fetchTools = useCallback(async () => {
    mcpLogger.time('fetchTools');
    mcpLogger.debug('Iniciando fetch de tools...');
    
    setIsLoading(true);
    setError(null);
    
    try {
      apiLogger.debug(`Llamando a: ${JARVIS_API}/api/v1/mcp/tools`);
      
      const response = await fetch(`${JARVIS_API}/api/v1/mcp/tools`);
      
      if (!response.ok) {
        mcpLogger.warn(`Response no OK: ${response.status} ${response.statusText}`);
        throw new Error('Error fetching tools');
      }
      
      const data = await response.json();
      
      mcpLogger.group('Tools fetched', () => {
        mcpLogger.debug('Total tools:', data.tools?.length || 0);
        mcpLogger.table(data.tools);
      });
      
      setTools(data.tools || []);
      setIsConnected(true);
      
      mcpLogger.success('Tools cargados exitosamente');
      
    } catch (err) {
      mcpLogger.error('Error al obtener MCP tools:', err);
      setError(err.message);
      setIsConnected(false);
    } finally {
      setIsLoading(false);
      mcpLogger.timeEnd('fetchTools');
    }
  }, []);

  useEffect(() => {
    mcpLogger.info('Hook useMCPTools montado, iniciando fetch...');
    fetchTools();
  }, [fetchTools]);

  // Función reconnect para refrescar los datos
  const reconnect = useCallback(async () => {
    mcpLogger.info('Reconectando MCP...');
    await fetchTools();
  }, [fetchTools]);

  return { 
    tools,
    prompts,
    resources,
    isLoading, 
    error,
    isConnected,
    reconnect       
  };
};