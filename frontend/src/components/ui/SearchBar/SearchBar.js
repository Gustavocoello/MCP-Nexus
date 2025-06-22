import React, { useState, useRef, useEffect } from 'react';
import './SearchBar.css';
import '../../../styles/App.css';
import { GrLink } from "react-icons/gr";
import { VscSettings } from "react-icons/vsc";
import { FaArrowUp, FaStop } from 'react-icons/fa';
import { MdOutlineAttachFile } from "react-icons/md";
// import { CgMathPlus } from "react-icons/cg";


const SearchBar = ({ onSearch, showIcon, isStreaming, onStop, onScrollToBottom }) => {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);

  // Ajustar altura del textarea basado en contenido, con máximo de 100px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'; // reset height
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 100) + 'px'; // altura máxima 100px
    }
  }, [query]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && query.trim()) {
      e.preventDefault();
      triggerSearch();
    }
  };

  const triggerSearch = () => {
    if (query.trim()) {
      onSearch(query);
      setQuery('');
    }
  };

  useEffect(() => {
  const handleClickOutside = (event) => {
    if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
      setShowMenu(false);
    }
  };

  document.addEventListener("mousedown", handleClickOutside);
  return () => document.removeEventListener("mousedown", handleClickOutside);
}, []);

  return (
    <div className="search-bar-container">
        {/*Icono de jarvis en el searchbar*/}
        <img 
          src="/icons/jarvis.png" 
          alt="Jarvis Icon" 
           className={`jarvis-icon ${!showIcon ? 'invisible-placeholder' : ''}`} 
          onClick={onScrollToBottom} 
        />
      

      {/* Botón + */}
      <div className="plus-menu-container" ref={dropdownRef}>
        <VscSettings
          className="plus-icon"
          onClick={() => setShowMenu(!showMenu)}
        />
        {showMenu && (
          <div className="dropdown-menu">
            <div className="menu-item" onClick={() => alert("developing")}>
              <GrLink className="menu-icon" />
              <span className="menu-label">tool Kit - MCP </span>
            </div>
            <div className="menu-item" onClick={() => alert("developing")}>
              <MdOutlineAttachFile className="menu-icon" />
              <span className="menu-label">Agregar imagenes y archivos</span>
            </div>
          </div>
        )}
      </div>

      {/* Área de búsqueda */}
      <div className="textarea-container">
        <textarea
          ref={textareaRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Search..."
          rows={1}
          className={`search-textarea ${query ? 'expanded' : 'collapsed'}`}
        />

       {isStreaming ? (
          <FaStop 
            onClick={onStop}
            className="stop-icon"
            aria-label="Stop generation"
            role="button"
            tabIndex={0}
          />
        ) : (
          <FaArrowUp 
            onClick={triggerSearch}
            className="arrow-icon"
            aria-label="Search"
            role="button"
            tabIndex={0}
            onKeyPress={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                triggerSearch();
              }
            }}
          />
        )}
      </div>
    </div>
  );
};

export default SearchBar;