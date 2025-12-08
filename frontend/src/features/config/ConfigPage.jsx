// src/features/config/ConfigPage.jsx
import { useNavigate, useLocation, useParams } from 'react-router-dom';
import ConfigDrawer from './components/ConfigDrawer';
import './components/ConfigDrawer.css';

const ConfigPage = () => {
  const navigate = useNavigate();

  const handleClose = () => {
    navigate(-1); // vuelve a la ruta anterior (como cerrar modal)
  };

  return <ConfigDrawer onClose={handleClose} />;
};

export default ConfigPage;
