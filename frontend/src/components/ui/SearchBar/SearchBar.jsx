import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactDOM from 'react-dom';
import './SearchBar.css';
import '../../../styles/App.css';
import { GrLink } from "react-icons/gr";
import { VscSettings } from "react-icons/vsc";
import { FaArrowUp, FaStop } from 'react-icons/fa';
import { MdOutlineAttachFile } from "react-icons/md";
import { IoCloseOutline } from "react-icons/io5";
import { extractFileContent } from '../../../service/api_service';
import { SiGooglecalendar } from "react-icons/si";
import { FaGithub } from 'react-icons/fa';
import { SiMysql } from 'react-icons/si';
import { IoIosClose } from "react-icons/io";
import { useMcpClient } from '../../../service/mcp_service';


const SearchBar = ({ onSearch, showIcon, isStreaming, onStop, onScrollToBottom, onContextExtracted, pendingContext, onRemoveContext,}) => {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);
  const dropdownRef = useRef(null);
  const fileInputRef = useRef(null);
  const [showMenu, setShowMenu] = useState(false);
  const [pendingFilePreview, setPendingFilePreview] = useState([]);
  const [serviceMenu, setServiceMenu] = useState(false);
  const [toolMenu, setToolMenu] = useState(false);
  const [selectedService, setSelectedService] = useState(null);
  const [selectedTool, setSelectedTool] = useState(null);
  const [selectedToolTab, setSelectedToolTab] = useState(null);
  const [toolConfirmed, setToolConfirmed] = useState(false); 
  const modalRef = useRef(null);

  // ----------------- SEARCHBAR LOGIC -----------------
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
    const lastUploadedImage = localStorage.getItem('lastUploadedImage');
    const shouldSendImage = pendingFilePreview.length > 0 && lastUploadedImage;
    const imageToSend = shouldSendImage ? lastUploadedImage : null;

    if (query.trim() || imageToSend) {
      onSearch(query, pendingContext, imageToSend, toolConfirmed && selectedTool ? selectedTool : "");
    }
    //Resetear selección de tool después de enviar
    setSelectedService(null);
    setSelectedTool(null);
    setSelectedToolTab(null);
    setToolConfirmed(false);

    // Resetar input y archivos
    setQuery('');
    setPendingFilePreview([]);
    localStorage.removeItem('lastUploadedImage');
};

  const handleFileSelect = () => {
    fileInputRef.current.click();
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
          progress: 0,
          loading: false
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
              f.name === file.name ? { ...f, progress: 100, loading: false } : f
            )
          );
        } catch (err) {
          console.error('Error al subir imagen:', err.message);
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
        setServiceMenu(false);
        setToolMenu(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);


// ----------------- MCP TOOL LOGIC ----------------
  const availableServices = [
  { id: 'google_calendar', name: 'Google Calendar', icon: <SiGooglecalendar />, dev: false },
  { id: 'github', name: 'GitHub', icon: <FaGithub />, dev: true },
  { id: 'mysql', name: 'MySQL', icon: <SiMysql />, dev: true }
  ];

  const {
    state,
    tools = [],
    prompts = [],
    resources = [],
    error,
    callTool,
    getPrompt,
    readResource,
    retry,
    authenticate
  } = useMcpClient();
  const connected = state === 'ready';



  const handleServiceClick = () => {
    setServiceMenu(!serviceMenu);
    setToolMenu(false);
  };

  const onSelectService = (service) => {
    setSelectedService(service);
    setSelectedToolTab(null);
    setSelectedTool(null);
    setToolMenu(true);
  };

  const handleSelectToolTab = (tab) => {
    if (selectedToolTab === tab) {
      setSelectedToolTab(null);
    } else {
      setSelectedToolTab(tab);
    }
  };

  const handleSelectTool = (toolName) => {
    setSelectedTool(toolName);
    setToolConfirmed(true); // marcar como confirmado
    setShowMenu(false);
    setServiceMenu(false);
    setToolMenu(false);
  };

  // Inicializa la herramienta seleccionada
  useEffect(() => {
    if (tools.length && !selectedTool) setSelectedTool(tools[0].name);
  }, [tools, selectedTool]);


  
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
        onClick={() => {
          const newShow = !showMenu;
          setShowMenu(newShow);
          if (!newShow) {
            setServiceMenu(false);
            setToolMenu(false);
          }
        }}
      />
      {showMenu && (
        <div className="dropdown-menu">
          <div className="menu-item" 
            onClick={() => {
              setServiceMenu(true);
            }}
          >
            <GrLink className="menu-icon"/>
            <span className="menu-label">Tool Kit - MCP</span>
          </div>
          {serviceMenu && (
            <div className="dropdown-submenu">
              {availableServices.map(svc => (
                <div
                  key={svc.id}
                  className="menu-items-service"
                  onClick={() => onSelectService(svc)}
                >
                  <span className="service-icon">{svc.icon}</span>
                  <span className="service-name">{svc.name}</span>
                  {svc.dev && <span className="service-dev">(En desarrollo)</span>}
                </div>
              ))}
            </div>
          )}

          {/* ------- MENÚ DE HERRAMIENTAS -------*/}
          {toolMenu && selectedService &&
            ReactDOM.createPortal(
              <div className="modal-overlay" onClick={handleOverlayClick}>
                <div className="modal-content" ref={modalRef} onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <span className="service-icon">{selectedService.icon}</span>
                    <h3 className="modal-title">{selectedService.name}</h3>
                  </div>

                  <div className="tool-tabs">
                    <button onClick={() => handleSelectToolTab('tools')}>🛠 Tools</button>
                    <button onClick={() => handleSelectToolTab('prompts')}>📝 Prompts</button>
                    <button onClick={() => handleSelectToolTab('resources')}>📚 Resources</button>
                  </div>

                  {selectedToolTab === 'tools' && (
                    !connected ? (
                      <div className="empty-message">
                        MCP no conectado. Estado: <strong>{state}</strong><br />
                        {error && <div>Error: {error}</div>}
                        <button onClick={authenticate}>Autenticar</button>
                        {state === 'failed' && <button onClick={retry}>Reintentar</button>}
                      </div>
                    ) : tools.length > 0 ? (
                      <div className="tool-list">
                        {tools.map(t => (
                          <div key={t.name} className="menu-item-tools" onClick={() => handleSelectTool(t.name)}>
                            {t.name}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-message">No hay tools disponibles.</div>
                    )
                  )}

                  {selectedToolTab === 'prompts' && (
                    !connected ? (
                      <div className="empty-message">
                        MCP no conectado. Estado: <strong>{state}</strong><br />
                        {error && <div>Error: {error}</div>}
                        <button onClick={authenticate}>Autenticar</button>
                        {state === 'failed' && <button onClick={retry}>Reintentar</button>}
                      </div>
                    ) : prompts.length > 0 ? (
                      <div className="tool-list">
                        {prompts.map(([key, prompt]) => (
                          <div key={key} className="menu-item-tools">{prompt.description || key}</div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-message">No hay prompts disponibles.</div>
                    )
                  )}

                  {selectedToolTab === 'resources' && (
                    !connected ? (
                      <div className="empty-message">
                        MCP no conectado. Estado: <strong>{state}</strong><br />
                        {error && <div>Error: {error}</div>}
                        <button onClick={authenticate}>Autenticar</button>
                        {state === 'failed' && <button onClick={retry}>Reintentar</button>}
                      </div>
                    ) : resources.length > 0 ? (
                      <div className="tool-list">
                        {resources.map(([key, resource]) => (
                          <div key={key} className="menu-item-tools">{resource.type || key}</div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-message">No hay recursos disponibles.</div>
                    )
                  )}

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
    {toolConfirmed && selectedTool && selectedService && (
      <div className="selected-tool">
        <span>{selectedService.name} {selectedToolTab} ➜ {selectedTool}</span>
        <IoIosClose
          className="clear-selection-icon"
          onClick={() => {
            setSelectedService(null);
            setSelectedTool(null);
            setSelectedToolTab(null);
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