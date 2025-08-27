import React, { useState, useEffect } from 'react';
import useCurrentUser from '../../../../auth/components/context/useCurrentUser';
import { loginWithGoogle, loginWithGitHub } from '../../../../auth/components/authService';
import { useMcpClient } from '../../../../../service/mcp_service';
import { FaGithub } from 'react-icons/fa';
import { FcGoogle } from 'react-icons/fc';
//import { SiGooglecalendar } from "react-icons/si";
import './McpTab.css';

const McpTab = () => {
  const { user } = useCurrentUser();
  const [activeTab, setActiveTab] = useState('tools');

  const {
    state,
    tools = [],
    prompts = [],
    resources = [],
    //callTool,      // Searchbar
    //readResource,  // Searchbar
    //getPrompt,     // Searchbar
    log,
    //retry,
    authenticate,
    error,
    start,
    //stop,
  } = useMcpClient();

  useEffect(() => {
    console.log('[MCP TAB]', { state, tools, prompts, resources, error });
  }, [state, tools, prompts, resources, error]);

   useEffect(() => {
    if (state === "ready") {
      // Busca cualquier mensaje que mencione "session" (la cabecera mcp-session-id aparece en los logs)
      const initLog = log.find(l => /session-id/i.test(l.message));
      console.log("%cMCP session-id:", "font-weight:bold", initLog?.message ?? "🤔 no capturado");
    }
  }, [state, log]);

  // Servicios externos Google/GitHub
  const services = [
    {
      name: 'Google',
      icon: <FcGoogle size={20} />,
      connected: user?.auth_provider === 'google',
      loginFn: loginWithGoogle
    },
    {
      name: 'GitHub',
      icon: <FaGithub size={20} />,
      connected: user?.auth_provider === 'github',
      loginFn: loginWithGitHub
    }
  ];

  // Estado de conexión MCP
   const connected = state === 'ready';

  // Conversión a arrays legibles si vienen como objeto
  const mcpTools = Array.isArray(tools) ? tools : Object.entries(tools);
  const mcpPrompts = Array.isArray(prompts) ? prompts : Object.entries(prompts);
  const mcpResources = Array.isArray(resources) ? resources : Object.entries(resources);

  return (
    <div className="mcp-tab-container">
      <h3>Servicios</h3>
      <div className="service-status-list">
        {services.map((s) => (
          <div key={s.name} className="service-status-item">
            <span className="service-icon">{s.icon}</span>
            <span className="service-name">{s.name}</span>
            {s.connected ? (
              <button className="status-button connected">Conectado</button>
            ) : (
              <button className="status-button disconnected" onClick={s.loginFn}>
                No conectado
              </button>
            )}
          </div>
        ))}
      </div>

      <hr className="divider" />

      <h3>Servicios MCP disponibles</h3>
      {!connected ? (
        <div className="mcp-status">
          <p>
            Estado MCP: <strong>{state}</strong>
            {error && <span> &mdash; Error: {error}</span>} Servidor no disponible.
          </p>
          {state === 'failed' && (
            <div className="mcp-actions">
              <button onClick={start}>Reintentar</button>
              <button onClick={() => authenticate({ state: { returnTo: '/config' } })}>
                Autenticar
              </button>
            </div>
          )}
          {state === 'idle' && (
            <button onClick={start}>Conectar manualmente</button>
          )}
        </div>
      ) : (
        <div className="mcp-panel">
          <div className="tabs">
            <div
              className={`tab ${activeTab === 'tools' ? 'active' : ''}`}
              onClick={() => setActiveTab('tools')}
            >
              🛠 Tools
            </div>
            <div
              className={`tab ${activeTab === 'prompts' ? 'active' : ''}`}
              onClick={() => setActiveTab('prompts')}
            >
              📝 Prompts
            </div>
            <div
              className={`tab ${activeTab === 'resources' ? 'active' : ''}`}
              onClick={() => setActiveTab('resources')}
            >
              📚 Resources
            </div>
          </div>

          <div className="panel-content">
            {activeTab === 'tools' && (
              <div className="mcp-service-card">
                {mcpTools.length === 0 ? (
                  <p>No hay tools disponibles.</p>
                ) : (
                  <>
                    <p className="section-title">Herramientas disponibles</p>
                    <ul>
                      {mcpTools.map((tool, idx) => {
                        const t = tool.name ? tool : tool[1];
                        const name = tool.name || tool[0];
                        return (
                          <li key={name}>
                            <strong>{name}</strong>: {t.description || 'Sin descripción'}
                          </li>
                        );
                      })}
                    </ul>
                  </>
                )}
              </div>
            )}
            {activeTab === 'prompts' && (
              <div className="mcp-service-card">
                {mcpPrompts.length === 0 ? (
                  <p>No hay prompts disponibles.</p>
                ) : (
                  <>
                    <p className="section-title">Prompts disponibles</p>
                    <ul>
                      {mcpPrompts.map(([key, prompt]) => (
                        <li key={key}>{prompt.description || 'Sin descripción'}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
            {activeTab === 'resources' && (
              <div className="mcp-service-card">
                {mcpResources.length === 0 ? (
                  <p>No hay resources disponibles.</p>
                ) : (
                  <>
                    <p className="section-title">Recursos disponibles</p>
                    <ul>
                      {mcpResources.map(([key, resource]) => (
                        <li key={key}>Tipo: {resource.type}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default McpTab;
