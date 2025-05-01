import React from 'react';
import SearchBarPrompt from './components/searchBarPrompt'; // Importa el componente combinado
import './App.css';

function App() {
  return (
    <div className="App" style={{ backgroundColor: 'black', minHeight: '100vh' }}>
      <header className="App-header">
        <h1 style={{ color: 'white', marginBottom: '30px' }}>Buscador de IA</h1>
        <SearchBarPrompt /> {/* Componente único con lógica integrada */}
      </header>
    </div>
  );
}

export default App;