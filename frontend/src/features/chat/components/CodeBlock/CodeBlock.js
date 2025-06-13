import React, { useState, useRef, useEffect } from 'react';
import { FaCheck } from 'react-icons/fa';
import { IoCopy } from 'react-icons/io5';
import hljs from 'highlight.js';
import './github-dark.css'
import 'highlight.js/styles/github-dark.css';
import './CodeBlock.css';

const CodeBlock = ({ code, language, isHtml = false }) => {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef(null);

  useEffect(() => {
    if (!isHtml && codeRef.current) {
      setTimeout(() => {
        hljs.highlightElement(codeRef.current);
      }, 0);
    }
  }, [code, language, isHtml]);

  const handleCopy = () => {
    // Si viene con highlight, eliminamos el HTML
    const plainText = isHtml
      ? codeRef.current?.textContent
      : code;

    navigator.clipboard.writeText(plainText || '');
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
        <code
          ref={codeRef}
          className={`hljs language-${language}`}
          {...(isHtml
            ? { dangerouslySetInnerHTML: { __html: code } }
            : { children: code })}
        />
      </pre>
    </div>
  );
};

export default CodeBlock;
