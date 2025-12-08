import { GiAstronautHelmet } from "react-icons/gi";
import { useNavigate } from "react-router-dom";
import { useAuthContext } from '@/features/auth/components/context/AuthContext';
import { useAuth } from '@clerk/clerk-react';
import "./Navbar.css";

const Navbar = ({ isWhiteTheme }) => {
  const { isAuthenticated } = useAuthContext();
  const { isLoaded } = useAuth();
  const navigate = useNavigate();

  const tooltip = !isLoaded
    ? "Cargando..."
    : isAuthenticated
    ? "Logeado"
    : "Identifícate";

  const handleAstronautClick = () => {
    if (!isAuthenticated) {
      navigate("/login");
    } else {
      navigate("/"); 
    }
  };


  return (
    <nav className={`navbar ${isWhiteTheme ? 'white-theme' : ''}`}>
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
          <li><a href="#home">Home</a></li>
          <li><a href="#services">Services</a></li>
          <li><a href="#developer">Developer</a></li>
        </ul>

        {/* Derecha: Astronauta */}
        <button
          className="astronaut-btn"
          onClick={handleAstronautClick}
          title={tooltip}
          aria-label={tooltip}
          disabled={!isLoaded} // deshabilita si está autenticado
        >
          <GiAstronautHelmet className="astronaut-icon" />
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
