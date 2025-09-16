import React from 'react';
import MarkdownIt from 'markdown-it';
import hljs from 'highlight.js';
import CodeBlock from '../components/CodeBlock/CodeBlock';

// Configuramos MarkdownIt con soporte de syntax highlighting
const md = new MarkdownIt({
  html: false,
  linkify: true,
  highlight: function (str, lang) {
    const validLang = hljs.getLanguage(lang) ? lang : 'plaintext';
    try {
      const highlighted = hljs.highlight(str, { language: validLang }).value;
      return `<pre><code class="language-${validLang}">${highlighted}</code></pre>`;
    } catch (_) {
      return `<pre><code>${md.utils.escapeHtml(str)}</code></pre>`;
    }
  }
});

const MarkdownRenderer = ({ content = '', stable = true }) => {
  const html = md.render(content);
  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = html;

  const elements = Array.from(tempDiv.childNodes).map((node, i) => {
    if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'PRE') {
      const codeEl = node.querySelector('code');
      if (!codeEl) return null;

      const rawCode = codeEl.textContent ?? '';
      const langClass = codeEl.getAttribute('class') || '';
      const language = langClass.replace('language-', '') || 'plaintext';

      const isProbablyInline = rawCode.length < 30 && !rawCode.includes('\n');
      if (isProbablyInline) {
        return (
          <code key={i} className="inline-fix">
            {rawCode}
          </code>
        );
      }

      const highlighted = !stable && hljs.getLanguage(language)
        ? hljs.highlight(rawCode, { language }).value
        : rawCode;

      return (
        <CodeBlock
          key={i}
          code={highlighted}
          language={language}
          stable={stable}
          isHtml={!stable}
        />
      );
    }

    return (
      <div
        key={i}
        className="message-html"
        dangerouslySetInnerHTML={{ __html: node.outerHTML }}
      />
    );
  });

  return <>{elements}</>;
};

export default MarkdownRenderer;
