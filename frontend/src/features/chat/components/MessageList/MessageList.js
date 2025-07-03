import React, { useRef } from 'react';
import CodeBlock from '../CodeBlock/CodeBlock';
import './MessageList.css'; // Archivo CSS modificado
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';
import MarkdownRenderer from '../../utils/MarkdownRenderer';

//import { marked } from 'marked';


const MessageList = ({ messages = [] }) => {
  const messagesEndRef = useRef(null);

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
    <div className="message-list">
      {filteredMessages.map((msg, index) => (
        <div key={msg.id || index} className={`message ${msg.role}`}>
          <div className="message-bubble">
              {msg.role === 'assistant' && msg.content ? (
                <MarkdownRenderer 
                content={msg.content}
                stable={msg.stable ?? false}
                />
              ) : (
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