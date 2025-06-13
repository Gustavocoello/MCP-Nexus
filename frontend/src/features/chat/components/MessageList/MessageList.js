import React, { useRef, useEffect } from 'react';
import CodeBlock from '../CodeBlock/CodeBlock';
import './MessageList.css'; // Archivo CSS modificado
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

//import { marked } from 'marked';


const MessageList = ({ messages = [] }) => {
  const messagesEndRef = useRef(null);

  const renderContent = (html, keyPrefix) => {
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = html;

  return Array.from(tempDiv.childNodes).map((node, i) => {
    const key = `${keyPrefix}-${i}`;

    if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'PRE' && node.querySelector('code')) {
      const codeEl = node.querySelector('code');
      const langClass = codeEl.className || '';
      const language = langClass.replace('language-', '') || 'plaintext';
      // New para lo colores en el codeBlock en el streaming
      const highlighted = hljs.highlight(codeEl.textContent, { language }).value;
      return (
        <CodeBlock
          key={key}
          code={highlighted}
          language={language}
          isHtml={true} // le avisa al CodeBlock que ya viene con highlight
        />
      );


    }

    return (
      <div
        key={key}
        className="message-html"
        dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(node.outerHTML || '') }}
      />
    );
  });  
};
  
useEffect(() => {
    hljs.highlightAll();
  }, [messages]);


  return (
    <div className="message-list">
      {messages.map((msg, index) => (
        <div key={msg.id || index} className={`message ${msg.role}`}>
          <div className="message-bubble">
            {renderContent(msg.html, msg.id || index)}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;