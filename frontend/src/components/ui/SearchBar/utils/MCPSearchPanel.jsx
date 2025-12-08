// components/MCPSearchPanel.jsx
import React, { useState } from 'react';
import { useMCPClient } from '@/components/controller/hooks/useMCPClient';
import { useMCPTools } from '@/components/controller/hooks/useMCPClientSimple';
import { FaGithub, FaDatabase } from 'react-icons/fa';
import { SiNotion, SiMysql } from 'react-icons/si';
import { FcGoogle } from 'react-icons/fc';
import { AiOutlineCloudServer } from 'react-icons/ai';
import { IoDocumentTextOutline } from 'react-icons/io5';
import { VscTools } from 'react-icons/vsc';
import { GrResources } from 'react-icons/gr';
import { TfiReload } from "react-icons/tfi";
import { GiArmoredBoomerang } from "react-icons/gi";
import { mcpLogger } from '@/components/controller/log/logger.jsx';
import '@/features/config/components/tabs/McpTab/McpTab.css';

const MCPSearchPanel = ({ onClose, onSelectTool }) => {
  const [activeTab, setActiveTab] = useState('tools');
  const { 
    isConnected, 
    isLoading, 
    error, 
    tools: serverTools, 
    prompts: serverPrompts, 
    resources: serverResources, 
    reconnect 
  } = useMCPTools();

  // Mapeo de servicios con sus iconos
  const serviceIcons = {
    google_calendar: <FcGoogle size={16} />,
    google: <FcGoogle size={16} />,
    notion: <SiNotion size={16} color="#fff" />,
    github: <FaGithub size={16} color="#fff" />,
    mysql: <SiMysql size={16} color="#4479A1" />,
    default: <FaDatabase size={16} color="#fff" />
  };

  // Función para obtener el servicio desde el nombre de la herramienta
  const getServiceFromToolName = (toolName) => {
    if (toolName.startsWith('google_calendar_')) return 'google_calendar';
    if (toolName.startsWith('google_')) return 'google';
    if (toolName.startsWith('notion_')) return 'notion';
    if (toolName.startsWith('github_')) return 'github';
    if (toolName.startsWith('mysql_')) return 'mysql';
    return 'default';
  };

  // Función para obtener nombre amigable del servicio
  const getServiceDisplayName = (service) => {
    const names = {
      google_calendar: 'Google Calendar',
      google: 'Google',
      notion: 'Notion',
      github: 'GitHub',
      mysql: 'MySQL',
      default: 'Otro'
    };
    return names[service] || service;
  };

  // Función para limpiar el nombre de la herramienta para mostrar
  const cleanToolName = (toolName) => {
    return toolName
      .replace(/^(google_calendar_|google_|notion_|github_|mysql_)/, '')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, l => l.toUpperCase());
  };

  // Server Real - Agrupar herramientas por servicio
  const groupedServerTools = (serverTools || []).reduce((acc, tool) => {
    const service = getServiceFromToolName(tool.name);
    if (!acc[service]) acc[service] = [];
    acc[service].push(tool);
    return acc;
  }, {});

  // Función para refrescar datos MCP
  const handleRefresh = async () => {
    try {
      await reconnect();
    } catch (err) {
      mcpLogger.error('Error al actualizar servidor MCP:', err);
    }
  };

  const handleSimulate = () => {
    mcpLogger.info('Simulación activada');
  };

  const handleToolSelect = (toolName) => {
    if (onSelectTool) {
      onSelectTool(toolName);
    }
  };

  return (
    <div className="mcp-tab-container">
      <div className="modal-close-header">
        <h3 className="mcp-section-header">
          <AiOutlineCloudServer size={24} />
          Servidores MCP
        </h3>
      </div>

      {/* Tabs */}
      <div className="tabs">
        {[
          { id: 'tools', label: 'Tools', icon: <VscTools size={18} /> },
          { id: 'prompts', label: 'Prompts', icon: <IoDocumentTextOutline size={18} /> },
          { id: 'resources', label: 'Resources', icon: <GrResources size={18} /> }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab ${activeTab === tab.id ? 'active' : ''}`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="panel-content">
        {activeTab === 'tools' && (
          <div>
            <h4 className="panel-content-header">
              Herramientas disponibles ({serverTools.length})
            </h4>
            
            {!isConnected ? (
              <div className="empty-message">
                <p>MCP no conectado. Estado: <strong>{isLoading ? 'Conectando...' : 'Desconectado'}</strong></p>
                {error && <p>Error: {error}</p>}
              </div>
            ) : Object.entries(groupedServerTools).length === 0 ? (
              <div className="empty-message">
                <p>No hay herramientas disponibles.</p>
              </div>
            ) : (
              Object.entries(groupedServerTools).map(([service, tools]) => (
                <div key={service} className="service-group">
                  <div className="service-group-header">
                    <span className="service-group-icon">
                      {serviceIcons[service]}
                    </span>
                    <span className="service-group-name">
                      {getServiceDisplayName(service)}
                    </span>
                    <span className="service-group-count">
                      {tools.length} herramienta{tools.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  
                  <div className="service-tools-grid">
                    {tools.map((tool) => (
                      <div 
                        key={tool.name} 
                        className="tool-card clickable" 
                        onClick={() => handleToolSelect(tool.name)}
                      >
                        <div className="tool-card-name">
                          {cleanToolName(tool.name)}
                        </div>
                        <div className="tool-card-description">
                          {tool.description}
                        </div>
                        <div className="tool-card-id">
                          {tool.name}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'prompts' && (
          <div>
            <h4 className="panel-content-header">
              Prompts disponibles ({serverPrompts.length})
            </h4>
            {!isConnected ? (
              <div className="empty-message">
                <p>MCP no conectado.</p>
              </div>
            ) : serverPrompts.length === 0 ? (
              <p className="empty-message">No hay prompts disponibles.</p>
            ) : (
              <div className="items-grid">
                {serverPrompts.map((prompt, idx) => (
                  <div key={idx} className="prompt-card">
                    <strong className="prompt-card-name">{prompt.name}</strong>
                    <p className="prompt-card-description">
                      {prompt.description}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'resources' && (
          <div>
            <h4 className="panel-content-header">
              Recursos disponibles ({serverResources.length})
            </h4>
            {!isConnected ? (
              <div className="empty-message">
                <p>MCP no conectado.</p>
              </div>
            ) : serverResources.length === 0 ? (
              <p className="empty-message">No hay recursos disponibles.</p>
            ) : (
              <div className="items-grid">
                {serverResources.map((resource, idx) => (
                  <div key={idx} className="resource-card">
                    <strong className="resource-card-name">{resource.name}</strong>
                    <p className="resource-card-type">
                      Tipo: {resource.type}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Botones de acción MCP */}
      <div className="mcp-actions">
        <button 
          className="mcp-action-button" 
          onClick={handleRefresh} 
          disabled={isLoading}
        >
          <TfiReload /> Actualizar
        </button>
        
        <button 
          className="mcp-action-button primary"
          onClick={handleSimulate}
        >
          <GiArmoredBoomerang /> Simular
        </button>
      </div>
    </div>
  );
};

export { MCPSearchPanel };