// src/features/config/components/ConfigDrawer.jsx
import { useState } from 'react';
import ThemeTab from './tabs/Theme/ThemeTab';
import MemoryTab from './tabs/MemoryTab/MemoryTab';
import GeneralTab from './tabs/General/GeneralTab';

const ConfigDrawer = ({ onClose }) => {
  const [activeTab, setActiveTab] = useState('general');

  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <h2>Configuración</h2>
          <button className="close-btn" onClick={onClose}>✖</button>
        </div>

        <div className="drawer-tabs">
          <button
            className={activeTab === 'general' ? 'active' : ''}
            onClick={() => setActiveTab('general')}
          >
            General
          </button>
          <button
            className={activeTab === 'tema' ? 'active' : ''}
            onClick={() => setActiveTab('tema')}
          >
            Tema
          </button>
          <button
            className={activeTab === 'memoria' ? 'active' : ''}
            onClick={() => setActiveTab('memoria')}
          >
            Administrar memoria
          </button>
        </div>

        <div className="drawer-divider" />

        <div className="drawer-content">
          {activeTab === 'general' && <GeneralTab />}
          {activeTab === 'tema' && <ThemeTab />}
          {activeTab === 'memoria' && <MemoryTab />}
        </div>
      </div>
    </div>
  );
};

export default ConfigDrawer;

