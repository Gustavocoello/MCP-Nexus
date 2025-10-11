import React, { useState } from 'react';
import { useMCPClient } from '@/components/controller/hooks/useMCPClient';
import { MCPSearchPanel } from '@/components/ui/SearchBar/utils/MCPSearchPanel';
import { FcGoogle } from 'react-icons/fc';
import { VscTools } from 'react-icons/vsc';
import { TfiReload } from "react-icons/tfi";
import { GrResources } from 'react-icons/gr';
import { AiOutlineCloudServer } from 'react-icons/ai';
import { FaGithub, FaDatabase } from 'react-icons/fa';
import { SiNotion, SiMysql, SiRed } from 'react-icons/si';
import { IoPrismOutline, IoDocumentTextOutline } from 'react-icons/io5';
import './McpTab.css';

const McpTab = () => {
  const [mainView, setMainView] = useState(''); // '', 'server', 'prueba'
  const [activeTab, setActiveTab] = useState('tools');
  const { isConnected, isLoading, error, tools: serverTools, prompts: serverPrompts, resources: serverResources, reconnect } = useMCPClient();

  
  // Simulando datos de ejemplo - Prueba
  const mockTools = [
    { name: 'google_calendar_create_event', description: 'Crea un nuevo evento en Google Calendar' },
    { name: 'google_calendar_delete_event', description: 'Elimina un evento de Google Calendar' },
    { name: 'google_calendar_daily_summary', description: 'Resumen diario de Google Calendar' },
    { name: 'notion_create_database', description: 'Crea una base de datos en Notion' },
    { name: 'notion_create_page', description: 'Crea una nueva página en Notion' },
    { name: 'github_create_repo', description: 'Crea un repositorio en GitHub' },
    { name: 'github_list_repos', description: 'Lista repositorios de GitHub' },
    { name: 'mysql_execute_query', description: 'Ejecuta una consulta MySQL' },
  ];

  const mockPrompts = [
    { name: 'calendar_meeting_scheduler', description: 'Asistente para programar reuniones' },
    { name: 'github_pr_reviewer', description: 'Revisor automático de Pull Requests' }
  ];

  const mockResources = [
    { name: 'google_calendar_data', type: 'calendar_events' },
    { name: 'notion_workspace', type: 'workspace_data' }
  ];

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

  // Agrupar herramientas por servicio
  const groupedTools = mockTools.reduce((acc, tool) => {
    const service = getServiceFromToolName(tool.name);
    if (!acc[service]) acc[service] = [];
    acc[service].push(tool);
    return acc;
  }, {});

  // Vista principal con los dos botones
  if (mainView === '') {
    return (
      <div className="mcp-main-view">
        <h2 className="mcp-main-title">Model Context Protocol</h2>
        
        <div className="mcp-main-buttons">
          {/* Botón Server */}
          <button
            onClick={() => setMainView('server')}
            className="mcp-main-button server"
          >
            <AiOutlineCloudServer size={48} color="#fff" />
            <span className="mcp-main-button-label">Server</span>
            <span className="mcp-main-button-description">
              Conectar con servidores MCP reales
            </span>
          </button>

          {/* Botón Prueba */}
          <button
            onClick={() => setMainView('prueba')}
            className="mcp-main-button prueba"
          >
            <IoPrismOutline size={48} color="#fff" />
            <span className="mcp-main-button-label">Prueba</span>
            <span className="mcp-main-button-description">
              Explorar funcionalidades de demostración
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
            Volver
          </button>
        </div>
      </div>
    );
  }

  // Vista Prueba (Mock)
  return (
    <div className="mcp-tab-container">
      <h3 className="mcp-section-header">
        <IoPrismOutline size={24} />
        Modo de Prueba - Servicios MCP
      </h3>
      
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
              Herramientas disponibles ({mockTools.length})
            </h4>
            
            {Object.entries(groupedTools).map(([service, tools]) => (
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
                    <div key={tool.name} className="tool-card">
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
            ))}
          </div>
        )}

        {activeTab === 'prompts' && (
          <div>
            <h4 className="panel-content-header">
              Prompts disponibles ({mockPrompts.length})
            </h4>
            {mockPrompts.length === 0 ? (
              <p className="empty-message">No hay prompts disponibles.</p>
            ) : (
              <div className="items-grid">
                {mockPrompts.map((prompt, idx) => (
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
              Recursos disponibles ({mockResources.length})
            </h4>
            {mockResources.length === 0 ? (
              <p className="empty-message">No hay recursos disponibles.</p>
            ) : (
              <div className="items-grid">
                {mockResources.map((resource, idx) => (
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

      {/* Estado de conexión MCP */}
      <div className="mcp-status">
        <span className="mcp-status-label">Estado MCP (Prueba):</span>{' '}
        <span className="mcp-status-value active">
          8 herramientas de demostración activas
        </span>
      </div>

      {/* Botones de acción MCP */}
      <div className="mcp-actions">
        <button className="mcp-action-button">
          🔄 Actualizar
        </button>
        
        <button className="mcp-action-button primary prueba">
          ⚡ Simular Conexión
        </button>
      </div>
      {/* Botón de volver abajo */}
      <div className="mcp-footer">
        <button
          onClick={() => setMainView('')}
          className="mcp-back-button red"
        >
          Volver
        </button>
      </div>
    </div>
  );
};

export default McpTab;