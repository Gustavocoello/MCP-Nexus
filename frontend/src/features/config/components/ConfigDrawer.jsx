// src/features/config/components/ConfigDrawer.jsx
import { useState } from 'react';
import ThemeTab from './tabs/Theme/ThemeTab';
import MemoryTab from './tabs/MemoryTab/MemoryTab';
import GeneralTab from './tabs/General/GeneralTab';
import McpTab from './tabs/McpTab/McpTab';

const ConfigDrawer = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState('general');
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [displayTab, setDisplayTab] = useState('general');

  const handleTabChange = (newTab) => {
    if (newTab === activeTab) return;
    
    setIsTransitioning(true);
    
    setTimeout(() => {
      setActiveTab(newTab);
      setDisplayTab(newTab);
      setIsTransitioning(false);
    }, 150);
  };

  return (
    <div className="drawer-backdrop drawer-backdrop-animated" onClick={onClose}>
      <div className="drawer-panel drawer-panel-animated" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2>Configuración</h2>
          <button className="close-btn" onClick={onClose}>✖</button>
        </div>

        <div className="drawer-tabs">
          <button
            className={activeTab === 'general' ? 'active' : ''}
            onClick={() => handleTabChange('general')}
          >
            General
          </button>
          <button
            className={activeTab === 'tema' ? 'active' : ''}
            onClick={() => handleTabChange('tema')}
          >
            Tema
          </button>
           <button
            className={activeTab === 'mcp' ? 'active' : ''}
            onClick={() => handleTabChange('mcp')}
          >
            MCP - Model Context Protocol
          </button>
          <button
            className={activeTab === 'memoria' ? 'active' : ''}
            onClick={() => handleTabChange('memoria')}
          >
            Administrar memoria
          </button>
        </div>

        <div className="drawer-divider" />

        <div className="drawer-content">
          <div className={`content-wrapper-config ${isTransitioning ? 'transitioning' : ''}`}>
            {displayTab === 'general' && <GeneralTab />}
            {displayTab === 'tema' && <ThemeTab />}
            {displayTab === 'memoria' && <MemoryTab />}
            {displayTab === 'mcp' && <McpTab />}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfigDrawer;