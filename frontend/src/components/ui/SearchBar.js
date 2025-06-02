import React, { useState, useRef, useEffect } from 'react';
import { FaArrowUp } from 'react-icons/fa';
import '../../styles/App.css'; // Asumiendo que App.css estará en la misma carpeta o en ruta correcta

const SearchBar = ({ onSearch, showIcon }) => {
  const [query, setQuery] = useState('');
  const textareaRef = useRef(null);

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

  return (
    <div className="search-bar-container">
      {showIcon && (
        <img 
          src="/icons/jarvis.png" 
          alt="Jarvis Icon" 
          className="jarvis-icon" 
        />
      )}

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
      </div>
    </div>
  );
};

export default SearchBar;

