import React from 'react';
import './Sidebar.css';

const Sidebar = () => {
  return (
    <div className="sidebar">
      <div className="sidebar-item">
        <span className="icon">Icon</span>
        <span className="label">Home</span>
      </div>
      <div className="sidebar-item">
        <span className="icon">Icon</span>
        <span className="label">Dashboard</span>
      </div>
      <div className="sidebar-item">
        <span className="icon">Icon</span>
        <span className="label">Settings</span>
      </div>
    </div>
  );
};

export default Sidebar;
