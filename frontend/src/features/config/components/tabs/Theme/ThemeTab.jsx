import React, { useEffect, useState } from 'react';
import './ThemeTab.css';
import BackgroundTechPattern from './BackgroundTechPattern';


const ThemeTab = () => {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('preferred-theme') || 'system';
  });

  useEffect(() => {
    if (theme === 'system') {
      const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      document.documentElement.setAttribute('data-theme', systemPrefersDark ? 'dark' : 'light');
    } else {
      document.documentElement.setAttribute('data-theme', theme);
    }

    // Guardar en localStorage
    localStorage.setItem('preferred-theme', theme);
  }, [theme]);

  const handleThemeChange = (e) => {
    setTheme(e.target.value);
  };

  //const handleAddCustomTheme = () => {
  //  alert('Funcionalidad para agregar temas personalizados próximamente.');
  //};

  return (
    <div className="theme-container">
      {theme === 'custom' && <BackgroundTechPattern />}

      <h3>Tema</h3>
      <p>Aquí podrás seleccionar el tema de la interfaz.</p>

      <div className="theme-group">
        <label className="theme-label" htmlFor="theme-select">Tema:</label>
        <select
          id="theme-select"
          value={theme}
          onChange={handleThemeChange}
          className="theme-select"
        >
          <option value="system">Sistema</option>
          <option value="dark">Oscuro</option>
          <option value="light">Claro</option>
        </select>
      </div>

      <div className="theme-group">
        <label className="theme-label">Tema personalizado:</label>

        <div className="theme-preview">
          <div className="preview-box">
            <p>Vista previa de tu fondo</p>
          </div>
          <button className="theme-button-personal" onClick={() => setTheme('custom')}>
            Aplicar tema personalizado
          </button>
        </div>
      </div>
    </div>
  );
};

export default ThemeTab;
