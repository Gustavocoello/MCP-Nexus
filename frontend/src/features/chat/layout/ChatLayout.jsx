// features/chat/layout/ChatLayout.js
import Sidebar from '../../../components/layout/Sidebar/Sidebar';
import { Outlet } from 'react-router-dom';
import BackgroundTechPattern from '../../config/components/tabs/Theme/BackgroundTechPattern';

export default function ChatLayout({ theme }) {
  return (
    <div className="app-container">
      {theme === 'custom' && <BackgroundTechPattern />}
      <Sidebar />
      <div className="main-content">
        <Outlet />
      </div>
    </div>
  );
}
