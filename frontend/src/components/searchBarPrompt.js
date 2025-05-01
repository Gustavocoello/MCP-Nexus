import React, { useState } from 'react';
import onPrompt from './service/api_service'; // Asegúrate de que la ruta sea correcta

const SearchBarPrompt = () => {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('');
  const [error, setError] = useState('');

  const handleKeyPress = async (e) => {
    if (e.key === 'Enter' && query.trim()) {
      await fetchResult(query);
    }
  };

  const handleClick = async () => {
    if (query.trim()) {
      await fetchResult(query);
    }
  };

  const fetchResult = async (promptText) => {
    try {
      const response = await onPrompt(promptText); // Llama al backend
      setResult(response?.result || response); // Ajusta según la estructura de tu respuesta
      setError('');
    } catch (err) {
      setError('Error al procesar el prompt');
      console.error(err.message);
    }
  };

  return (
    <div style={{ textAlign: 'center', margin: '50px 0' }}>
      {/* Barra de búsqueda */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '20px' }}>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Escribe un prompt..."
          style={{
            padding: '15px',
            borderRadius: '30px',
            border: '2px solid white',
            flex: 1,
            maxWidth: '500px',
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
          Enviar
        </button>
      </div>

      {/* Resultado o error */}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {result && <p style={{ marginTop: '20px', fontSize: '20px' }}>{result}</p>}
    </div>
  );
};

export default SearchBarPrompt;