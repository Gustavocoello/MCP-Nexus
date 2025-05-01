import React, { useState } from 'react';

const SearchBar = ({ onSearch }) => {
  const [query, setQuery] = useState('');

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      onSearch(query);
    }
  };

  const handleClick = () => {
    if (query.trim()) {
      onSearch(query);
    }
  };

  return (
    <div style={{ 
      display: 'flex',
      margin: '30px auto',
      width: '80%',
      maxWidth: '600px',
      justifyContent: 'center'
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
          fontSize: '18px',
          backgroundColor: 'black',
          color: 'white'
        }}
      />
      <button
        onClick={handleClick}
        style={{
          marginLeft: '15px',
          padding: '15px 30px',
          borderRadius: '30px',
          border: '2px solid white',
          backgroundColor: 'black',
          color: 'white',
          cursor: 'pointer',
          fontSize: '18px',
          fontWeight: 'bold'
        }}
      >
        Search
      </button>
    </div>
  );
};

export default SearchBar;
