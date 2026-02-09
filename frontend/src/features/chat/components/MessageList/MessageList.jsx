///features/chat/components/Messagelist.jsx
import React, { useEffect, useCallback, useRef } from 'react';
import CodeBlock from '../CodeBlock/CodeBlock';
import './MessageList.css'; // Archivo CSS modificado
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import MarkdownRenderer from '../../utils/MarkdownRenderer';

const MessageList = ({ messages = [], onLoadMore, hasMore }) => {
  const messagesEndRef = useRef(null);
  const containerRef = useRef(null);
  const loadingRef = useRef(false);

  //Detectar scroll arriba
  const handleScroll = useCallback(() => {
    if (!containerRef.current || loadingRef.current || !hasMore) return;

    const { scrollTop } = containerRef.current;
    
    // Si está cerca del tope (menos de 100px)
    if (scrollTop < 100) {
      loadingRef.current = true;
      onLoadMore?.();
      setTimeout(() => {
        loadingRef.current = false;
      }, 1000);
    }
  }, [hasMore, onLoadMore]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll);
    return () => container.removeEventListener('scroll', handleScroll);
  }, [handleScroll]);

  const filteredMessages = messages.filter(
    msg => !msg.html?.includes('[NOTIFICATION]')
  );

  const renderContent = (msg, keyPrefix) => {
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = msg.html;

  return Array.from(tempDiv.childNodes).map((node, i) => {
    const key = `${keyPrefix}-${i}`;

    if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'PRE') {
      const codeEl = node.querySelector('code');
      if (!codeEl) {
        return (
          <div
            key={key}
            className="message-html"
            dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(node.outerHTML || '') }}
          />
        );
      }

      const content = codeEl.textContent.trim();
      const isProbablyInline = content.length < 30 && !content.includes('\n');
      if (isProbablyInline) {
        return <code key={key} className="inline-fix">{content}</code>;
      }

      const langClass = codeEl.getAttribute('class') || '';
      let language = langClass.replace('language-', '') || 'plaintext';

      if (!hljs.getLanguage(language)) language = 'plaintext';

      // ✅ IMPORTANTE: solo resaltar si msg.stable es false
      const highlighted = msg.stable
        ? content // ya está procesado por hljs
        : hljs.highlight(content, { language }).value;

      return (
        <CodeBlock
          key={key}
          code={highlighted}
          language={language}
          isHtml={!msg.stable}
          stable={msg.stable ?? true}
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


/*  
useEffect(() => {
    hljs.highlightAll();
  }, [messages]);
*/

return (
  <div className="message-list" ref={containerRef}>
    {hasMore && (
        <div className="load-more-indicator">
          Scroll arriba para cargar mensajes antiguos...
        </div>
      )}
    {filteredMessages.map((msg, index) => (
      <div 
      key={msg.id || index} 
      id={`msg-${msg.id}`}
      className={`message ${msg.role}`}>
        <div className="message-bubble">
          {/* 🖼️ Renderizar imágenes base64 directamente */}
          {msg.type === 'image' ? (
            <img
              src={msg.imageUrl || msg.content}
              alt="Imagen enviada"
              className="chat-image-upload"
            />
          ) : msg.role === 'assistant' && msg.content ? (
            // 📄 Mensajes del asistente con Markdown
            <MarkdownRenderer
              content={msg.content}
              stable={msg.stable ?? false}
            />
          ) : (
            // 🧱 Otros mensajes con HTML o código
            renderContent(msg, msg.id || index)
          )}
        </div>
      </div>
    ))}
    <div ref={messagesEndRef} />
  </div>
  );
};

export default MessageList;