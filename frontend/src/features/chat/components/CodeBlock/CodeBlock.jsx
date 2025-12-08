import React, { useState, useRef, useEffect } from 'react';
import { FaCheck } from 'react-icons/fa';
import { IoCopy } from 'react-icons/io5';
import { streamLogger } from '@/components/controller/log/logger.jsx';
import hljs from 'highlight.js';
import './github-dark.css';
import 'highlight.js/styles/github-dark.css';
import './CodeBlock.css';

const CodeBlock = ({ code, language, isHtml = false, stable = false }) => {
  const [copied, setCopied] = useState(false);
  const codeRef = useRef(null);

  useEffect(() => {
    streamLogger.info(`[CodeBlock] useEffect run: stable=${stable}, isHtml=${isHtml}`);
    if (!codeRef.current) return;

     const el = codeRef.current;

    // ✅ Evita resaltar dos veces
    if (stable && !el.dataset.highlighted) {
      hljs.highlightElement(el);
      el.dataset.highlighted = 'true';
      streamLogger.info(`[CodeBlock] Highlight aplicado al final:`, el);
    }
  }, [code, language, isHtml, stable]);

  useEffect(() => {
    streamLogger.info(`[CodeBlock] Render - language: ${language} | stable: ${stable}`);
  }, [code, stable, language]);

  const handleCopy = () => {
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
  };

  const displayLanguage = languageNames[language] || language || 'Code';

  // 🎯 BONUS: lógica separada y clara
  const renderCode = () => {
    const className = `hljs language-${language}`;
    return isHtml ? (
      <code
        ref={codeRef}
        className={className}
        dangerouslySetInnerHTML={{ __html: code }}
      />
    ) : (
      <code ref={codeRef} className={className}>
        {code}
      </code>
    );
  };

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
              <span>Copiar código</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-content">{renderCode()}</pre>
    </div>
  );
};

export default CodeBlock;

