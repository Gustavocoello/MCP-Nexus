// src/features/config/ConfigPage.jsx
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import ConfigDrawer from './components/ConfigDrawer';
import './components/ConfigDrawer.css';

const ConfigPage = () => {
  const navigate = useNavigate();
  const { userId } = useParams();

  const handleClose = () => {
    // 1. Verificamos si tenemos el userId
    if (userId) {
      navigate(`/c/${userId}`, { replace: true });
    } else {
      navigate('/', { replace: true });
    }
  };

  return <ConfigDrawer onClose={handleClose} />;
};

export default ConfigPage;
