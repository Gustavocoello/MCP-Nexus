import React from 'react';
import SearchBar from './components/SearchBar';
import './App.css';

function App() {
  const handleSearch = (query) => {
    alert(`Searching for: ${query}`);
  };

  return (
    <div className="App" style={{ backgroundColor: 'black', minHeight: '100vh' }}>
      <header className="App-header" style={{ backgroundColor: 'black' }}>
        <SearchBar onSearch={handleSearch} />
      </header>
    </div>
  );
}

export default App;
