// frontend/src/features/config/components/tabs/McpTab/McpTab.jsx
import React, { useState } from 'react';
import McpTestMode from './components/McpTestMode';
import { useEffect } from "react";
import { useLocation } from "react-router-dom";
import { MCPSearchPanel } from '@/components/ui/SearchBar/utils/MCPSearchPanel';
import { useConnectGoogleCalendar } from "@/features/auth/services/authServices.jsx";
import { FcGoogle } from 'react-icons/fc';
import { AiOutlineCloudServer } from 'react-icons/ai';
import { SiNotion, SiMysql, SiMicrosoftaccess} from 'react-icons/si';
import { IoPrismOutline, } from 'react-icons/io5';
import { FaGithub, FaCheckCircle, FaTimesCircle} from 'react-icons/fa';
import {  apiLogger, mcpLogger } from '@/components/controller/log/logger.jsx';
import apiClient from '@/service/api';
import './McpTab.css';

const McpTab = () => {
  const [mainView, setMainView] = useState(''); // '', 'server', 'prueba'
  const location = useLocation();

  // Simulación del servicio para obtener datos
  // NOTA: Reemplaza esto con tu llamada real a la API (fetch/axios)
  const integrationApi = {
    getStatus: async () => {
      // GET /api/v1/integrations/status
      const response = await apiClient.get('/api/v1/integrations/status'); 
      return response.data; // Axios devuelve los datos en la propiedad .data
    },
    disconnect: async (provider) => {
      // POST /api/v1/integrations/disconnect/<provider>
      const response = await apiClient.post(`/api/v1/integrations/disconnect/${provider}`);
      return response.data;
    }
  };

  const fetchIntegrationStatus = async () => {
    try {
      const status = await integrationApi.getStatus();
      setServiceConnections(prev => ({ ...prev, ...status }));
    } catch (error) {
      apiLogger.error("Error fetching integration status:", error);
      // Manejar error de forma visible si es necesario
    }
  };

  // Cargar el estado al montar y al cambiar location (post-callback)
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const connectionSuccess = params.get("connection_success"); // Nuevo parámetro del backend
    const connectionError = params.get("error");

    fetchIntegrationStatus();

    if (connectionSuccess) {
      // La conexión fue exitosa (Google Calendar, etc.)
      alert(`Connection successful: ${connectionSuccess.replace('_', ' ')}`);
      
      // 1. Recargar el estado de conexión (ya se hace con fetchIntegrationStatus() arriba)
      // 2. Limpiar la URL después de procesar
      window.history.replaceState({}, "", location.pathname);
    } else if (connectionError) {
      alert(`Connection failed: ${params.get("details") || connectionError}`);
      // Limpiar la URL después de procesar
      window.history.replaceState({}, "", location.pathname);
    }
    
    // Volver a ejecutar cuando la URL o el estado del location cambien
  }, [location.search]);

  const connectGoogleCalendar = useConnectGoogleCalendar();
  
  const [serviceConnections, setServiceConnections] = useState({
    google_calendar: false,
    github: false,
    microsoft_access: false,
    notion: false,
    mysql: false,
  });

  const [connectingService, setConnectingService] = useState(null);

  const handleServiceConnect = async (serviceName) => {
    setConnectingService(serviceName);
    try {
        if (serviceName === 'google_calendar') {
          // LÓGICA ESPECÍFICA PARA GOOGLE CALENDAR (REDIRECCIÓN)
          await connectGoogleCalendar();
          return; 
          
        } else {
          // LÓGICA DE SIMULACIÓN PARA OTROS SERVICIOS (GitHub, Notion, MySQL, etc.)
          await new Promise(resolve => setTimeout(resolve, 1500));
          
          setServiceConnections(prev => ({
            ...prev,
            [serviceName]: true
          }));
          
          alert(`${serviceName} connected successfully (Simulated)`);
        }

      } catch (error) {
        apiLogger.error(`[MCPTAB] Error connecting to ${serviceName}:`, error);
        alert(`Connection failed for ${serviceName}: ${error.message || error}`);
      } finally {
        if (serviceName !== 'google_calendar') {
            setConnectingService(null);
        }
      }
    };

    const handleServiceDisconnect = async (serviceName) => {
      try{
      // 1. Llamada a la API de desconexión (Real para Google Calendar)
        await integrationApi.disconnect(serviceName); 
        // 2. Recargar el estado completo desde el backend
        await fetchIntegrationStatus();
        alert(`${serviceName} disconnected`)
      } catch (error) {
        apiLogger.error(`Error disconnecting ${serviceName}:`, error);
      }
    };
    
    // ServiceConnectionCard (se mantiene igual)
    const ServiceConnectionCard = ({ service, icon, name, description, connected, onConnect, onDisconnect, isConnecting, badge }) => (
      <div className={`service-connection-card ${connected ? 'connected' : ''}`}>
        {/* ... Resto del contenido de la tarjeta ... */}
        <div className="service-connection-header">
          <div className="service-connection-icon">
            {icon}
          </div>
          <div className="service-connection-info">
            <h4 className="service-connection-name">
              {name}
              {badge && <span className="service-connection-badge developing"> {badge}</span>}
            </h4>
            <p className="service-connection-description">{description}</p>
          </div>
          <div className="service-connection-status">
            {connected ? (
              <FaCheckCircle className="status-icon connected" />
            ) : (
              <FaTimesCircle className="status-icon disconnected" />
            )}
          </div>
        </div>
        
        <div className="service-connection-actions">
          {!connected ? (
            <button
              className="service-connect-btn"
              onClick={() => onConnect(service)}
              disabled={isConnecting}
            >
              {isConnecting ? 'Conectando...' : 'Conectar'}
            </button>
          ) : (
            <button
              className="service-disconnect-btn"
              onClick={() => onDisconnect(service)}
            >
              Disconnect
            </button>
          )}
        </div>
      </div>
    );
  // Vista principal con los dos botones
  if (mainView === '') {
    return (
      <div className="mcp-main-view">
        <h2 className="mcp-main-title">Model Context Protocol</h2>

        {/* Service Connections Section */}
        <div className="service-connections-section">
          <h4 className="service-connections-title">Connect Services</h4>
          <div className="service-connections-grid">
            {/* Google Calendar */}
            <ServiceConnectionCard
              service="google_calendar"
              icon={<FcGoogle size={32} />}
              name="Google Calendar"
              description="Manage events and reminders"
              connected={serviceConnections.google_calendar}
              onConnect={handleServiceConnect} 
              onDisconnect={handleServiceDisconnect}
              isConnecting={connectingService === 'google_calendar'}
            />
            {/* GitHub */}
            <ServiceConnectionCard
              service="github"
              icon={<FaGithub size={32} color="#fff" />}
              name="GitHub"
              description="Manage repositories and PRs"
              connected={serviceConnections.github}
              onConnect={handleServiceConnect}
              onDisconnect={handleServiceDisconnect}
              isConnecting={connectingService === 'github'}
            />
            {/* Microsoft Access */}
            <ServiceConnectionCard
              service="microsoft_access"
              icon={<SiMicrosoftaccess size={32} color="#B01D1D" />}
              name="Microsoft Access"
              description="Connect and query local Access databases"
              connected={serviceConnections.microsoft_access}
              onConnect={handleServiceConnect}
              onDisconnect={handleServiceDisconnect}
              isConnecting={connectingService === 'microsoft_access'}
              badge="Developing"
            />
            {/* Notion */}
            <ServiceConnectionCard
              service="notion"
              icon={<SiNotion size={32} color="#fff" />}
              name="Notion"
              description="Interact with pages and databases"
              connected={serviceConnections.notion}
              onConnect={handleServiceConnect}
              onDisconnect={handleServiceDisconnect}
              isConnecting={connectingService === 'notion'}
              badge="Developing"
            />

            {/* Nueva tarjeta: MySQL */}
            <ServiceConnectionCard
              service="mysql"
              icon={<SiMysql size={32} color="#4479A1" />}
              name="MySQL"
              description="Execute queries against your database"
              connected={serviceConnections.mysql}
              onConnect={handleServiceConnect}
              onDisconnect={handleServiceDisconnect}
              isConnecting={connectingService === 'mysql'}
              badge="Developing"
            />
          </div>
        </div>

        <h3 className="mcp-section-header">
          <IoPrismOutline size={24} />
          Test Mode - MCP Services
        </h3>

        <div className="mcp-main-buttons">
          {/* Server Button */}
          <button
            onClick={() => setMainView('server')}
            className="mcp-main-button server"
          >
            <AiOutlineCloudServer size={48} color="#fff" />
            <span className="mcp-main-button-label">Server</span>
            <span className="mcp-main-button-description">
              Connect to real MCP servers
            </span>
          </button>

          {/* Test Button */}
          <button
            onClick={() => setMainView('prueba')}
            className="mcp-main-button prueba"
          >
            <IoPrismOutline size={48} color="#fff" />
            <span className="mcp-main-button-label">Test</span>
            <span className="mcp-main-button-description">
              Explore demo functionalities
            </span>
          </button>
        </div>
      </div>
    );
  }

  // Vista Server
  if (mainView === 'server') {
    return (
      <div className="mcp-tab-container">
        {/* Renderizamos directamente MCPSearchPanel */}
        <MCPSearchPanel />

        {/* Botón de volver abajo */}
        <div className="mcp-footer">
          <button
            onClick={() => setMainView('')}
            className="mcp-back-button red"
          >
            Back
          </button>
        </div>
      </div>
    );
  }

  // Vista Prueba (Mock)
  if (mainView === 'prueba') {
    return (
      <McpTestMode setMainView={setMainView} />
    );
  }
};

export default McpTab;