# src/services/rag/chunker.py
from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

# ─────────────────────────────────────────────────────────────
#  Mapa de extensión → Language enum de LangChain
#  Agrega más si Koda trabaja con otros lenguajes
# ─────────────────────────────────────────────────────────────
EXTENSION_TO_LANGUAGE: dict[str, Language] = {
    # Python
    ".py":    Language.PYTHON,
    # JavaScript / TypeScript
    ".js":    Language.JS,
    ".jsx":   Language.JS,
    ".ts":    Language.TS,
    ".tsx":   Language.TS,
    # Web
    ".html":  Language.HTML,
    ".htm":   Language.HTML,
    # Markdown / docs
    ".md":    Language.MARKDOWN,
    ".mdx":   Language.MARKDOWN,
    # Rust
    ".rs":    Language.RUST,
    # Go
    ".go":    Language.GO,
    # Ruby
    ".rb":    Language.RUBY,
    # C / C++
    ".c":     Language.C,
    ".cpp":   Language.CPP,
    ".h":     Language.CPP,
    # Java / Kotlin
    ".java":  Language.JAVA,
    ".kt":    Language.KOTLIN,
    # Shell
    ".sh":    Language.MARKDOWN,   # no tiene nativo, markdown es suficiente
    # SQL → sin Language nativo, usamos separadores custom
    ".sql":   None,
    # JSON / YAML → texto plano
    ".json":  None,
    ".yaml":  None,
    ".yml":   None,
    ".toml":  None,
    ".env":   None,
}

# Separadores custom para SQL (LangChain no tiene Language.SQL)
SQL_SEPARATORS = [
    "\n\n",        # bloques separados por línea en blanco
    ";\n",         # fin de sentencia
    "\n",
    " ",
    "",
]


class DocumentChunker:
    """
    Chunker inteligente para Koda.
    - Detecta el lenguaje por extensión del filename
    - Usa RecursiveCharacterTextSplitter.from_language() para código
      (respeta funciones, clases y bloques completos)
    - Fallback a separadores genéricos para texto plano / desconocido
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size    = chunk_size
        self.chunk_overlap = chunk_overlap

        # Splitter genérico — para texto plano, JSON, YAML, etc.
        self._default_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", " ", ""],
        )

        # Splitter SQL custom
        self._sql_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=SQL_SEPARATORS,
        )

    # ─────────────────────────────────────────────────────────
    #  API pública
    # ─────────────────────────────────────────────────────────

    def chunk_text(self, text: str, filename: str = "") -> list[str]:
        """
        Punto de entrada principal.

        Uso:
            chunks = chunker.chunk_text(content, filename="auth/token_validator.py")
            chunks = chunker.chunk_text(content, filename="schema.sql")
            chunks = chunker.chunk_text(content)   # fallback genérico
        """
        if not text:
            return []

        splitter = self._get_splitter(filename)
        chunks   = splitter.split_text(text)

        # Filtra chunks vacíos o con solo espacios
        return [c for c in chunks if c.strip()]

    def detect_language(self, filename: str) -> str:
        """
        Retorna el nombre legible del lenguaje detectado.
        Útil para logging y para el metadata del Document.
        """
        lang = self._detect_language_enum(filename)
        if lang is None:
            ext = self._get_extension(filename)
            return ext.lstrip(".").upper() if ext else "plaintext"
        return lang.value   # ej: "python", "js", "ts"

    # ─────────────────────────────────────────────────────────
    #  Internals
    # ─────────────────────────────────────────────────────────

    def _get_splitter(self, filename: str) -> RecursiveCharacterTextSplitter:
        ext  = self._get_extension(filename)
        lang = EXTENSION_TO_LANGUAGE.get(ext)   # None si no está en el mapa

        # SQL → separadores custom
        if ext == ".sql":
            return self._sql_splitter

        # Lenguaje conocido → splitter específico (respeta bloques de código)
        if lang is not None:
            return RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )

        # Desconocido / texto plano → splitter genérico
        return self._default_splitter

    def _detect_language_enum(self, filename: str) -> Language | None:
        return EXTENSION_TO_LANGUAGE.get(self._get_extension(filename))

    @staticmethod
    def _get_extension(filename: str) -> str:
        """Extrae la extensión en minúsculas. Ej: 'Auth.PY' → '.py'"""
        if not filename:
            return ""
        idx = filename.rfind(".")
        return filename[idx:].lower() if idx != -1 else ""