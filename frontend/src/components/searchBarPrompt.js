import React, { useState } from 'react';
import SearchBar from './SearchBar';
import onPrompt from './service/api_service';
import MarkdownIt from 'markdown-it'; // Importa el paquete

const md = new MarkdownIt(); // Inicializa el parser

const SearchBarPrompt = () => {
  const [result, setResult] = useState('');

  const handleSearch = async (promptText) => {
    try {
      const response = await onPrompt(promptText);
      // Convierte el resultado de Markdown a HTML
      const htmlResult = md.render(response.result || '');
      setResult(htmlResult);
    } catch (error) {
      console.error(error.message);
    }
  };

  return (
    <div>
      <SearchBar onSearch={handleSearch} />
      {/* Muestra el resultado como HTML */}
      <div dangerouslySetInnerHTML={{ __html: result }} /> 
    </div>
  );
};

export default SearchBarPrompt;