import React, { useState } from 'react';

const SearchBar = ({ onSearch, showIcon }) => {
  const [query, setQuery] = useState('');

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && query.trim()) {
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
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'flex-start',
      gap: '10px',
      width: '80%',
      maxWidth: '600px',
      margin: '0 auto'
    }}>
      {/* Ícono condicional */}
      {showIcon && (
        <img 
          src="/icons/jarvis.png" 
          alt="Jarvis Icon" 
          style={{ flexShrink: 0 }} 
        />
      )}

      {/* Contenedor input + botón */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        flexWrap: 'nowrap',
        width: '100%',
        gap: '10px',
      }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Search..."
          style={{
            padding: '15px',
            borderRadius: '30px',
            border: '2px solid white',
            flex: 1,
            outline: 'none',
            fontSize: '16px',
            backgroundColor: 'black',
            color: 'white'
          }}
        />
        <button
          onClick={triggerSearch}
          style={{
            padding: '15px 30px',
            borderRadius: '30px',
            border: '2px solid white',
            backgroundColor: 'black',
            color: 'white',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: 'bold'
          }}
        >
          Search
        </button>
      </div>
    </div>
  );
};

export default SearchBar;