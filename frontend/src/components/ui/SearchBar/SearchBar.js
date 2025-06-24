import React, { useState, useRef, useEffect } from 'react';
import './SearchBar.css';
import '../../../styles/App.css';
import { GrLink } from "react-icons/gr";
import { VscSettings } from "react-icons/vsc";
import { FaArrowUp, FaStop } from 'react-icons/fa';
import { MdOutlineAttachFile } from "react-icons/md";

const REACT_APP = process.env.REACT_APP_URL;

const SearchBar = ({ onSearch, showIcon, isStreaming, onStop, onScrollToBottom, onImageUpload , onContextExtracted, pendingContext}) => {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);

  // Ajustar altura del textarea basado en contenido, con máximo de 100px
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 100) + 'px';
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
      onSearch(query, pendingContext);
      setQuery('');
    }
  };

  const handleFileSelect = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${REACT_APP}/api/chat/extract_file`, {
      method: 'POST',
      body: formData,
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'Error al extraer el archivo');

    // Enviar el texto extraído al LLM usando onSearch
    if (data.text) {
      onContextExtracted(data.text);  // Nueva prop que recibe ChatPage
    }

  } catch (err) {
    console.error('Error al procesar el archivo:', err.message);
    alert('Error al procesar el archivo: ' + err.message);
  } finally {
    e.target.value = null; // permite volver a seleccionar el mismo archivo
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

  // Extraer texto de archivos al seleccionar
  
  

  return (
    <div className="search-bar-container">
      {/* Input oculto para selección de archivos */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        style={{ display: 'none' }}
        accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.ppt,.pptx"
      />

      {/* Icono de jarvis en el searchbar */}
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
              <span className="menu-label">tool Kit - MCP</span>
            </div>
            <div className="menu-item" onClick={handleFileSelect}>
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
