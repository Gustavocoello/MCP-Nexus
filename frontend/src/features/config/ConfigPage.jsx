// src/features/config/ConfigPage.jsx
import ConfigDrawer from './components/ConfigDrawer';
//import { useJarvis } from '../../context/JarvisProvider';
import './components/ConfigDrawer.css';

const ConfigPage = ({ onCustomClose }) => {
  // Ahora la lógica de "cerrar" se la pasamos desde afuera
  // o usamos una por defecto.
  const handleClose = () => {
    if (onCustomClose) {
      onCustomClose();
    } else {
      console.log("Config cerrado");
    }
  };

  return <ConfigDrawer onClose={handleClose} />;
};

export default ConfigPage;