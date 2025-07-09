import React, { useState, useRef, useEffect, useCallback } from 'react';
import './SearchBar.css';
import '../../../styles/App.css';
import { GrLink } from "react-icons/gr";
import { VscSettings } from "react-icons/vsc";
import { FaArrowUp, FaStop } from 'react-icons/fa';
import { MdOutlineAttachFile } from "react-icons/md";
import { IoCloseOutline } from "react-icons/io5";
import { extractFileContent } from '../../../service/api_service';


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

    const allAreImages = files.every(file => file.type.startsWith("image/"));

    if (allAreImages) {
      await handleImageUploadOnly(files);
      e.target.value = null;
      return;
    }

    setShowMenu(false);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const fileType = file.type;

      let icon = '📎';
      if (fileType.includes('pdf')) icon = '📄';
      else if (fileType.includes('spreadsheet') || file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) icon = '📊';
      else if (fileType.includes('image')) icon = '🖼️';

      const previewUrl = fileType.includes('image') ? URL.createObjectURL(file) : null;

      const fileState = {
        name: file.name,
        type: fileType,
        icon,
        previewUrl,
        progress: 0,
        loading: true
      };

      setPendingFilePreview(prev => [...prev, fileState]);

      const formData = new FormData();
      formData.append('file', file);

      try {

        const data = await extractFileContent(file)

        if (data.text) {
          onContextExtracted({ name: file.name, text: data.text });
        }

        setPendingFilePreview(prev =>
          prev.map(f =>
            f.name === file.name ? { ...f, progress: 100, loading: false } : f
          )
        );
      } catch (err) {
        console.error('Error al procesar archivo:', err.message);
        alert('Error al procesar archivo: ' + err.message);

        setPendingFilePreview(prev =>
          prev.map(f =>
            f.name === file.name ? { ...f, progress: 100, loading: false } : f
          )
        );
      }
    }

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

  const handleImageUploadOnly = useCallback(async (images) => {
    setShowMenu(false); 
    for (let i = 0; i < images.length; i++) {
      const file = images[i];
      if (!file.type.startsWith("image/")) continue;

      const previewUrl = URL.createObjectURL(file);

      const fileState = {
        name: file.name,
        type: file.type,
        icon: '🖼️',
        previewUrl,
        progress: 0,
        loading: true
      };

      setPendingFilePreview(prev => [...prev, fileState]);

      const formData = new FormData();
      formData.append('file', file);

      try {
        
        const data = await extractFileContent(file);
        if (data.text) {
          onContextExtracted({ name: file.name, text: data.text });
        }

        setPendingFilePreview(prev =>
          prev.map(f =>
            f.name === file.name ? { ...f, progress: 100, loading: false } : f
          )
        );
      } catch (err) {
        console.error('Error al subir imagen:', err.message);
        alert('Error al subir imagen: ' + err.message);

        setPendingFilePreview(prev =>
          prev.map(f =>
            f.name === file.name ? { ...f, progress: 100, loading: false } : f
          )
        );
      }
    }
  }, [onContextExtracted]);




  // Para pasar imagenes desde el portapapeles
  useEffect(() => {
  const handlePaste = async (event) => {
    const items = event.clipboardData?.items;
    if (!items) return;

    const imageItems = Array.from(items).filter(item => item.type.startsWith("image/"));
    if (imageItems.length === 0) return;

    const files = imageItems.map(item => item.getAsFile()).filter(Boolean);
    if (files.length > 0) {
      await handleImageUploadOnly(files);
    }
  };

  document.addEventListener("paste", handlePaste);
  return () => document.removeEventListener("paste", handlePaste);
}, [handleImageUploadOnly]);


  
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
            {file.loading && (
              <div className="circular-progress-overlay">
                <svg className="circular-progress" viewBox="0 0 36 36">
                  <path
                    className="circle-bg"
                    d="M18 2.0845
                      a 15.9155 15.9155 0 0 1 0 31.831
                      a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <path
                    className="circle"
                    strokeDasharray={`${file.progress}, 100`}
                    d="M18 2.0845
                      a 15.9155 15.9155 0 0 1 0 31.831
                      a 15.9155 15.9155 0 0 1 0 -31.831"
                  />
                  <text x="18" y="20.35" className="percentage">{file.progress}%</text>
                </svg>
              </div>
            )}
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
      multiple
    />
  </div>
</div>

  
);
};

export default SearchBar;