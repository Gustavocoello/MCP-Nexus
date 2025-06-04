import React, { useRef, useEffect } from 'react';
import CodeBlock from '../CodeBlock/CodeBlock';
import { marked } from 'marked';
import './MessageList.css'; // Archivo CSS modificado

const MessageList = ({ messages = [] }) => {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const renderContent = (textOrHtml) => {
  const html = marked.parse(textOrHtml); // ✅ transforma Markdown a HTML
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = html;

  const nodes = [];
  tempDiv.childNodes.forEach((node, index) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      if (node.tagName === 'PRE' && node.querySelector('code')) {
        const codeElement = node.querySelector('code');
        const language = codeElement.className.replace('language-', '') || 'plaintext';
        nodes.push(
          <CodeBlock
            key={`code-${index}`}
            language={language}
            code={codeElement.textContent}
          />
        );
      } else {
        nodes.push(
          <div
            key={`html-${index}`}
            dangerouslySetInnerHTML={{ __html: node.outerHTML }}
            className="message-content"
          />
        );
      }
    } else if (node.nodeType === Node.TEXT_NODE) {
      nodes.push(
        <div key={`text-${index}`} className="message-text">
          {node.textContent}
        </div>
      );
    }
  });

  return nodes;
};


  return (
    <div className="message-list">
      {messages.map((msg, index) => (
        <div key={msg.id || index} className={`message ${msg.role}`}>
          <div className="message-bubble">
            {renderContent(msg.html)}
          </div>
        </div>
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;