import React, { useState, useRef, useEffect } from 'react';
import Prism from 'prismjs';
import 'prismjs/components/prism-javascript.min';
import 'prismjs/components/prism-python.min';
import 'prismjs/themes/prism-okaidia.min.css';
import { FaCheck } from 'react-icons/fa';
import { IoCopy } from "react-icons/io5";
import './CodeBlock.css'; // Archivo CSS para estilos personalizados

const CodeBlock = ({ code, language }) => {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef(null);

  useEffect(() => {
    Prism.highlightAll();
  }, [code, language]);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    
    // Efecto visual al copiar
    if (codeRef.current) {
      codeRef.current.classList.add('copied-effect');
      setTimeout(() => {
        if (codeRef.current) {
          codeRef.current.classList.remove('copied-effect');
        }
      }, 500);
    }
    
    setTimeout(() => setCopied(false), 2000);
  };

  // Mapeo de nombres de lenguaje
  const languageNames = {
    js: 'JavaScript',
    javascript: 'JavaScript',
    py: 'Python',
    python: 'Python',
    html: 'HTML',
    css: 'CSS',
    json: 'JSON',
    xml: 'XML',
    java: 'Java',
    cpp: 'C++',
    csharp: 'C#',
    ruby: 'Ruby',
    php: 'PHP',
    go: 'Go',
    sql: 'SQL',
    bash: 'Bash',
    r: 'R',
    kotlin: 'Kotlin',
    swift: 'Swift',
    typescript: 'TypeScript',
    jsx: 'JSX',
    // Añade más según necesites
  };

  const displayLanguage = languageNames[language] || language;

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
        <code ref={codeRef} className={`language-${language}`}>
          {code}
        </code>
      </pre>
    </div>
  );
};

export default CodeBlock;