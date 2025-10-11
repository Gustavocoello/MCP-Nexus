import { GiAstronautHelmet } from "react-icons/gi";
import { useNavigate } from "react-router-dom";
//import useCurrentUser from "../../../features/auth/components/context/useCurrentUser";
import useAuthStatus from '@/service/useAuthStatus';
import "./Navbar.css";

const Navbar = () => {
  const isAuthenticated = useAuthStatus();
  const navigate = useNavigate();

  const tooltip = isAuthenticated ? "Logeado" : "Identifícate";

  const handleAstronautClick = () => {
    if (!isAuthenticated) {
        navigate("/login");
    }
    // si está autenticado, no hace nada
    };


  return (
    <nav className="navbar">
      <div className="nav-inner">
        {/* Izquierda: Logo + nombre */}
        <div className="navbar-left">
          <div className="logo-box">
            {/* usa tu icono transparente */}
            <img
              src="/icons/galaxy-transparent.png"
              alt="Jarvis Logo"
              className="logo-img"
            />
          </div>
          <span className="logo-text">AI Assistant</span>
        </div>

        {/* Centro/Derecha: Links */}
        <ul className="navbar-links">
          <li><a href="#inicio">Inicio</a></li>
          <li><a href="#servicios">Servicios</a></li>
          <li><a href="#desarrollador">Desarrollador</a></li>
        </ul>

        {/* Derecha: Astronauta */}
        <button
          className="astronaut-btn"
          onClick={handleAstronautClick}
          title={tooltip}
          aria-label={tooltip}
          disabled={isAuthenticated} // deshabilita si está autenticado
        >
          <GiAstronautHelmet className="astronaut-icon" />
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
