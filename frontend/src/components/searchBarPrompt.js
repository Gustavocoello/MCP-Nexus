import React, { useState } from 'react';
import SearchBar from './SearchBar';
import onPrompt from './service/api_service';
import MarkdownIt from 'markdown-it';

const md = new MarkdownIt();

const SearchBarPrompt = ({ onNewMessage }) => {
  const [query, setQuery] = useState('');

  const handleKeyPress = async (e) => {
    if (e.key === 'Enter' && query.trim()) {
      // Notificar al padre (ChatPage) que el usuario escribió algo
      if (onNewMessage) {
        onNewMessage({ role: 'user', text: query });
        setQuery(''); // Limpiar el campo de entrada
        
      }

      try {
        const response = await onPrompt(query);

        // Convertir resultado a HTML si es necesario
        const htmlResult = md.render(response.result || '');

        // Notificar al padre (ChatPage) que Jarvis respondió
        if (onNewMessage) {
          onNewMessage({ role: 'jarvis', text: htmlResult }); // Envía el HTML
        }
      } catch (error) {
        console.error(error.message);
        if (onNewMessage) {
          onNewMessage({ role: 'jarvis', text: 'Hubo un error al procesar tu solicitud.' });
        }
      }

      setQuery('');
    }
  };

  return (
    <SearchBar
      value={query}
      onChange={(e) => setQuery(e.target.value)}
      onKeyPress={handleKeyPress}
    />
  );
};

export default SearchBarPrompt;