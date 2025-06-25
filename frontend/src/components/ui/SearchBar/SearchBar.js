import React, { useState, useRef, useEffect } from 'react';
import './SearchBar.css';
import '../../../styles/App.css';
import { GrLink } from "react-icons/gr";
import { VscSettings } from "react-icons/vsc";
import { FaArrowUp, FaStop } from 'react-icons/fa';
import { MdOutlineAttachFile } from "react-icons/md";
import { IoCloseOutline } from "react-icons/io5";


const REACT_APP = process.env.REACT_APP_URL;

const SearchBar = ({ onSearch, showIcon, isStreaming, onStop, onScrollToBottom, onImageUpload , onContextExtracted, pendingContext, onClearContext, onRemoveContext,}) => {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);
  const [pendingFilePreview, setPendingFilePreview] = useState([]);


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
      setPendingFilePreview([]);
    }
  };

  const handleFileSelect = () => {
    fileInputRef.current.click();
  };

  const handleFileChange = async (e) => {
  const files = Array.from(e.target.files);
  if (files.length === 0) return;

  setShowMenu(false); // cerrar el menú automáticamente

  const previews = [];

  for (const file of files) {
    const fileType = file.type;
    let icon = '📎';
    if (fileType.includes('pdf')) icon = '📄';
    else if (fileType.includes('spreadsheet') || file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) icon = '📊';
    else if (fileType.includes('image')) icon = '🖼️';

    let previewUrl = null;
    if (fileType.includes('image')) {
      previewUrl = URL.createObjectURL(file);
    }

    previews.push({
      name: file.name,
      type: fileType,
      icon,
      previewUrl,
    });

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${REACT_APP}/api/chat/extract_file`, {
        method: 'POST',
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || 'Error al extraer el archivo');
      if (data.text) {
        onContextExtracted({ name: file.name, text: data.text });
      }
    } catch (err) {
      console.error('Error al procesar archivo:', err.message);
      alert('Error al procesar archivo: ' + err.message);
    }
  }

  // Agrega todos los previews nuevos
  setPendingFilePreview(prev => [...prev, ...previews]);
  e.target.value = null;
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
    <div className="search-bar-wrapper">
  {/* Ícono Jarvis (afuera del campo redondeado) */}
  <img
    src="/icons/jarvis.png"
    alt="Jarvis Icon"
    className={`jarvis-icon ${!showIcon ? 'invisible-placeholder' : ''}`}
    onClick={onScrollToBottom}
  />

  {/* Caja redondeada que contiene todo lo que se expande */}
  <div className="search-box-container">
    {/* Vista previa del archivo */}
    {Array.isArray(pendingFilePreview) && pendingFilePreview.length > 0 && (
      <div className="file-preview-container-horizontal">
        {pendingFilePreview.map((file, index) => (
          <div className="file-preview-inside" key={index}>
            {file.previewUrl ? (
              <img src={file.previewUrl} alt="preview" className="file-preview-image" />
            ) : (
              <span className="file-icon">{file.icon}</span>
            )}
            <span className="file-name">{file.name}</span>
            <button
              className="remove-file-button"
              onClick={() => {
                const fileToRemove = pendingFilePreview[index];
                setPendingFilePreview(prev => prev.filter((_, i) => i !== index));
                onRemoveContext(fileToRemove.name);
              }}
              aria-label="Eliminar archivo"
            >
              <IoCloseOutline size={18} />
            </button>
          </div>
        ))}
      </div>
    )}

    {/* Campo de búsqueda */}


    {/* Textarea y botón enviar */}
    <div className="textarea-container">
      <textarea
        ref={textareaRef}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder="Search..."
        rows={1}
        className="search-textarea"
      />
      {isStreaming ? (
        <FaStop className="stop-icon" onClick={onStop} />
      ) : (
        <FaArrowUp className="arrow-icon" onClick={triggerSearch} />
      )}
    </div>

    {/* Botón + menú */}
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
            <span className="menu-label">Agregar imágenes y archivos</span>
          </div>
        </div>
      )}
    </div>

    {/* Input oculto para seleccionar archivos */}
    <input
      type="file"
      ref={fileInputRef}
      onChange={handleFileChange}
      style={{ display: 'none' }}
      accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.txt,.csv,.ppt,.pptx"
    />
  </div>
</div>

  
);
};

export default SearchBar;