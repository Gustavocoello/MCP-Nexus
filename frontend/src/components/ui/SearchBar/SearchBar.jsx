// frontend/src/components/ui/SearchBar/SearchBar.jsx
import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom';
import { MCPSearchPanel } from './utils/MCPSearchPanel';
import { extractFileContent } from '@/service/api_service';
import { IoIosClose } from "react-icons/io";
import { FaArrowUp, FaStop } from 'react-icons/fa';
import { MdOutlineAttachFile } from "react-icons/md";
import { GrLink, GrResources } from "react-icons/gr";
import { VscSettings, VscTools } from "react-icons/vsc";
import { IoCloseOutline, IoDocumentTextOutline } from "react-icons/io5";
import { apiLogger } from '@/components/controller/log/logger.jsx';
import './SearchBar.css';
import '@/styles/App.css';

const SearchBar = ({ onSearch, showIcon, isStreaming, onStop, onScrollToBottom, onContextExtracted, pendingContext, onRemoveContext,}) => {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);
  const [pendingFilePreview, setPendingFilePreview] = useState([]);
  const [toolMenu, setToolMenu] = useState(false);
  const [toolConfirmed, setToolConfirmed] = useState(false); 
  const modalRef = useRef(null);
  const [selectedTool, setSelectedTool] = useState(null);
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [selectedResource, setSelectedResource] = useState(null);
  const VITE_APP = import.meta.env.VITE_URL;


  // ----------------- SEARCHBAR LOGIC -----------------
  // Auto-ajustar altura del textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 100) + 'px';
    }
  }, [query]);

  // Para escuchar eventos de SSE
  useEffect(() => {
    let eventSource = new EventSource(`${VITE_APP}/api/chat/events`, {
      withCredentials: true 
    });

    eventSource.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.type === 'ping') return; // Ignorar el pulso de vida

      setPendingFilePreview(prev => prev.map(f => {
        // IMPORTANTE: Asegúrate de que event.filename coincida exactamente con f.name
        if (f.name === event.filename) {
          if (event.type === "upload_started") return { ...f, loading: true, progress: 60 };
          if (event.type === "upload_completed") return { ...f, loading: false, progress: 100 };
          if (event.type === "upload_error") return { ...f, loading: false, progress: 0, error: true };
        }
        return f;
      }));
    };

    eventSource.onerror = (err) => {
      apiLogger.error("SSE Error - Intentando reconectar...", err);
      eventSource.close();
      // Reintentar conexión tras 3 segundos si falla
      setTimeout(() => {
        // Aquí podrías disparar un estado para forzar la reconexión
      }, 3000);
    };

    return () => eventSource.close();
  }, [VITE_APP]);

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && query.trim()) {
      e.preventDefault();
      triggerSearch();
    }
  };

  const triggerSearch = () => {
    const lastUploadedImage = localStorage.getItem('lastUploadedImage');
    const shouldSendImage = pendingFilePreview.length > 0 && lastUploadedImage;
    const imageToSend = shouldSendImage ? lastUploadedImage : null;

    if (query.trim() || imageToSend) {
      apiLogger.info('TriggerSearch: Iniciando búsqueda', { query: query.length > 0, hasImage: !!imageToSend, tool: selectedTool || 'none' });
      onSearch(query, pendingContext, imageToSend, toolConfirmed && selectedTool ? selectedTool : "");
    }
    //Resetear selección de tool después de enviar
    setSelectedTool(null);
    setToolConfirmed(false);

    // Resetar input y archivos
    setQuery('');
    setPendingFilePreview([]);
    localStorage.removeItem('lastUploadedImage');
};

  const handleFileSelect = () => {
    fileInputRef.current.click();
    apiLogger.debug('FileSelect: Abriendo diálogo de archivos');
  };
  // ----------------- FILE UPLOAD LOGIC -----------------
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
        progress: 10,
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
            f.name === file.name ? { ...f, progress: 50} : f
          )
        );
      } catch (err) {
        apiLogger.error(`FileChange: Error al procesar archivo ${file.name}`, err.message);
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

  // ----------------- IMAGE UPLOAD LOGIC -----------------
  const handleImageUploadOnly = useCallback(async (images) => {
    setShowMenu(false);

    for (let i = 0; i < images.length; i++) {
      const file = images[i];
      if (!file.type.startsWith("image/")) continue;

      const reader = new FileReader();

      reader.onloadend = async () => {
        const base64Image = reader.result;

        // Guarda temporalmente en localStorage
        localStorage.setItem('lastUploadedImage', base64Image);

        const fileState = {
          name: file.name,
          type: file.type,
          icon: '🖼️',
          previewUrl: base64Image,
          file,
          progress: 10,
          loading: true
        };

        // Actualiza los estados visuales
        setPendingFilePreview(prev => [...prev, fileState]);

        try {
          const data = await extractFileContent(file);
          if (data.text) {
            onContextExtracted({ name: file.name, text: data.text });
          }

          setPendingFilePreview(prev =>
            prev.map(f =>
              f.name === file.name ? { ...f, progress: 50} : f
            )
          );
        } catch (err) {
          apiLogger.error(`ImageUpload: Error al subir imagen ${file.name}`, err.message);
          alert('Error al subir imagen: ' + err.message);
        }
      };

      reader.readAsDataURL(file);
    }
  }, [onContextExtracted]);

  useEffect(() => {
    // Por si quedó algo colgado
    localStorage.removeItem('lastUploadedImage');
  }, []);


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

// ----------------- MODAL LOGIC ----------------  
  const handleOverlayClick = (e) => {
    if (e.target.classList.contains('modal-overlay')) {
      setToolMenu(false);
    }
  };

  // Logica para el botón de cerrar el modal y todos 
  useEffect(() => {
    const handleClickOutside = (e) => {
      const clickedInsideDropdown = dropdownRef.current && dropdownRef.current.contains(e.target);
      const clickedInsideModal = modalRef.current && modalRef.current.contains(e.target);

      if (!clickedInsideDropdown && !clickedInsideModal) {
        setShowMenu(false);
        setToolMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
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
                // Limpiar del localstorage
                localStorage.removeItem('lastUploadedImage');
              }}
              aria-label="Eliminar archivo"
            >
              <IoCloseOutline size={18} />
            </button>
            {file.loading && (
              <div className="circular-progress-overlay">
                <svg className={`circular-progress ${file.error ? 'error' : ''}`} viewBox="0 0 36 36">
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
        onClick={() => {
          const newShow = !showMenu;
          setShowMenu(newShow);
          if (!newShow) {
            setToolMenu(false);
          }
        }}
      />
      {showMenu && (
        <div className="dropdown-menu">
          <div className="menu-item" 
            onClick={() => {
              setToolMenu(true);
            }}
          >
            <GrLink className="menu-icon"/>
            <span className="menu-label">Tool Kit - MCP</span>
          </div>
          {/* ------- MENÚ DE HERRAMIENTAS -------*/}
          {/* ------- MENÚ MCP COMPLETO -------*/}
          {toolMenu && 
            ReactDOM.createPortal(
              <div className="modal-overlay" onClick={handleOverlayClick}>
                <div className="modal-content mcp-modal" ref={modalRef} onClick={(e) => e.stopPropagation()}>
                  <MCPSearchPanel 
                    onClose={() => {
                      setToolMenu(false);
                      setShowMenu(false);
                    }}
                    onSelectTool={(toolName) => {
                      setSelectedTool(toolName);
                      setToolConfirmed(true);
                      setShowMenu(false);
                      setToolMenu(false);
                    }}
                    onSelectPrompt={(prompt) => {
                      setSelectedPrompt(prompt);
                      setToolConfirmed(true);
                      setShowMenu(false);
                      setToolMenu(false);
                    }}
                    onSelectResource={(res) => {
                      setSelectedResource(res);
                      setToolConfirmed(true);
                      setShowMenu(false);
                      setToolMenu(false);
                    }}
                  />
                </div>
              </div>,
              document.getElementById('modal-root')
            )
          }
          <div className="menu-item" onClick={handleFileSelect}>
            <MdOutlineAttachFile className="menu-icon" />
            <span className="menu-label">Agregar imágenes y archivos</span>
          </div>
        </div>
      )}
    </div>
    {/* --- Mostrar herramienta seleccionada --- */}
    {toolConfirmed && (
      <div className="selected-tool">
        {selectedTool && (
          <>
            <VscTools className="selected-tool-icon" size={16} />
            <span>{selectedTool}</span>
          </>
        )}
        {selectedPrompt && (
          <>
            <IoDocumentTextOutline className="selected-tool-icon" size={16} />
            <span>{selectedPrompt.name}</span>
          </>
        )}
        {selectedResource && (
          <>
            <GrResources className="selected-tool-icon" size={16} />
            <span>{selectedResource.name}</span>
          </>
        )}
        <IoIosClose
          className="clear-selection-icon"
          onClick={() => {
            setSelectedTool(null);
            setSelectedPrompt(null);
            setSelectedResource(null);
            setToolConfirmed(false);
          }}
        />
      </div>
    )}

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