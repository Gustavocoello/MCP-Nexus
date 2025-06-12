import React, { useState, useRef, useEffect } from 'react';
import { FaCheck } from 'react-icons/fa';
import { IoCopy } from 'react-icons/io5';
import hljs from 'highlight.js';
import 'highlight.js/styles/github-dark.css';
import './CodeBlock.css';

const CodeBlock = ({ code, language }) => {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef(null);

  useEffect(() => {
  if (codeRef.current) {
    hljs.highlightElement(codeRef.current);
  }
}, [code, language]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);

    if (codeRef.current) {
      codeRef.current.classList.add('copied-effect');
      setTimeout(() => {
        codeRef.current.classList.remove('copied-effect');
      }, 500);
    }

    setTimeout(() => setCopied(false), 2000);
  };

  const languageNames = {
    js: 'JavaScript',
    jsx: 'JSX',
    py: 'Python',
    ts: 'TypeScript',
    html: 'HTML',
    css: 'CSS',
    json: 'JSON',
    bash: 'Bash',
    sql: 'SQL',
    // agrega más si necesitas
  };

  const displayLanguage = languageNames[language] || language || 'Code';

  return (
    <div className="code-block">
      <div className="code-header">
        <span className="language-label">{displayLanguage}</span>
        <button className="copy-btn" onClick={handleCopy}>
          {copied ? (
            <>
              <FaCheck className="copy-icon copied" />
              <span>Copiado!</span>
            </>
          ) : (
            <>
              <IoCopy className="copy-icon" />
              <span>Copiar</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-content">
        <code ref={codeRef} className={`hljs language-${language}`}>
          {code}
        </code>
      </pre>
    </div>
  );
};

export default CodeBlock;
