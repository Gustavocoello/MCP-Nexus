import React from 'react';

const SearchBar = ({ value, onChange, onKeyPress }) => {
  const handleButtonClick = () => {
    if (value.trim()) {
      onKeyPress({ key: 'Enter' }); 
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
        value={value}
        onChange={onChange}
        onKeyPress={onKeyPress}
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
        onClick={handleButtonClick} // Llama a una función controladora
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