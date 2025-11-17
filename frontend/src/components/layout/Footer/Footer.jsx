import React from "react";
import { FaLinkedin, FaGithub } from "react-icons/fa";
import { BsTerminalSplit } from "react-icons/bs";
import { Link } from "react-router-dom";
import "./Footer.css";

const Footer = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="main-footer">
      {/* Sección principal del footer */}
      <div className="footer-content">
        {/* Columna izquierda: Logo + Social */}
        <div className="footer-brand">
          <div className="footer-logo-container">
            <img
              src="/icons/galaxy-transparent.png"
              alt="AI Assistant Logo"
              className="footer-logo-img"
            />
            <span className="footer-brand-name">AI Assistant</span>
          </div>
          
          <p className="footer-tagline">
            Empowering developers with intelligent AI tools
          </p>

          {/* Iconos sociales */}
          <div className="footer-social">
            <a
              href="https://www.linkedin.com/in/gustavocoelloo"
              target="_blank"
              rel="noreferrer"
              aria-label="LinkedIn"
            >
              <FaLinkedin />
            </a>
            <a
              href="https://github.com/Gustavocoello"
              target="_blank"
              rel="noreferrer"
              aria-label="GitHub"
            >
              <FaGithub />
            </a>
            <a
              href="https://cv-gus.vercel.app"
              target="_blank"
              rel="noreferrer"
              aria-label="Portfolio"
            >
              <BsTerminalSplit />
            </a>
          </div>
        </div>

        {/* Columnas de enlaces */}
        <div className="footer-columns">
          {/* Columna 1: About */}
          <div className="footer-column">
            <h4 className="footer-column-title">About</h4>
            <ul className="footer-links">
              <li><Link to="/overview">Overview</Link></li>
              <li><Link to="/mission">Mission</Link></li>
              <li><Link to="/contact">Contact</Link></li>
            </ul>
          </div>

          {/* Columna 2: Legal */}
          <div className="footer-column">
            <h4 className="footer-column-title">Legal</h4>
            <ul className="footer-links">
              <li><Link to="/privacy">Privacy Policy</Link></li>
              <li><Link to="/terms">Terms of Service</Link></li>
              <li><Link to="/data">Data Practices</Link></li>
            </ul>
          </div>

          {/* Columna 3: Resources */}
          <div className="footer-column">
            <h4 className="footer-column-title">Resources</h4>
            <ul className="footer-links">
              <li><Link to="/docs">Documentation</Link></li>
              <li><Link to="/api">API Reference</Link></li>
              <li><Link to="/guides">Developer Guides</Link></li>
            </ul>
          </div>
        </div>
      </div>

      {/* Barra inferior */}
      <div className="footer-bottom">
        <p>© {currentYear} AI Assistant — All rights reserved.</p>
      </div>
    </footer>
  );
};

export default Footer;