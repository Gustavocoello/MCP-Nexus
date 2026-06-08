# tools/ast_analyzer.py
import os
from typing import Optional

# ─────────────────────────────────────────────────────────────
#  Carga lazy — si falta un paquete solo falla ese lenguaje,
#  no todo el módulo
# ─────────────────────────────────────────────────────────────
def _load_languages() -> dict:
    langs = {}
    loaders = {
        ".py":   ("tree_sitter_python",     "language"),
        ".js":   ("tree_sitter_javascript",  "language"),
        ".jsx":  ("tree_sitter_javascript",  "language"),
        ".ts":   ("tree_sitter_typescript",  "language_typescript"),
        ".tsx":  ("tree_sitter_typescript",  "language_tsx"),
        ".go":   ("tree_sitter_go",          "language"),
        ".html": ("tree_sitter_html",        "language"),
        ".java": ("tree_sitter_java",        "language"),
        ".rb":   ("tree_sitter_ruby",        "language"),
        ".rs":   ("tree_sitter_rust",        "language"),
    }
    for ext, (module, func) in loaders.items():
        try:
            import importlib
            from tree_sitter import Language
            mod  = importlib.import_module(module)
            lang = Language(getattr(mod, func)())
            langs[ext] = lang
        except Exception:
            pass   # Lenguaje no instalado → simplemente no aparece
    return langs

LANGUAGE_MAP: dict = {}   # Se llena en el primer uso (lazy)

# ─────────────────────────────────────────────────────────────
#  Nodos que nos interesan, por lenguaje
#  Separados para evitar colisiones y duplicados
# ─────────────────────────────────────────────────────────────
TARGET_NODES = frozenset({
    # Python
    "class_definition",
    "function_definition",
    "decorated_definition",        # @tool, @app.route, @property …
    # JavaScript / TypeScript
    "class_declaration",
    "function_declaration",
    "method_definition",
    "arrow_function",
    "export_statement",            # export default / export const
    "lexical_declaration",         # const foo = () => {}
    "variable_declaration",
    # Java
    "method_declaration",
    "constructor_declaration",
    "class_declaration",
    # Go
    "function_declaration",
    "method_declaration",
    "type_declaration",
    # Ruby / Rust
    "method",
    "function_item",
    "impl_item",
})

MAX_DEPTH = 12   # Evita stack overflow en archivos muy anidados


# ─────────────────────────────────────────────────────────────
#  Extracción de nombre y firma
# ─────────────────────────────────────────────────────────────

def _get_text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _extract_name(node, source: bytes) -> str:
    """Extrae el nombre del nodo. Maneja casos especiales por tipo."""
    # decorated_definition → busca el nodo hijo real (function/class)
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type in ("function_definition", "class_definition"):
                return _extract_name(child, source)
        return "decorated"

    # variable_declaration / lexical_declaration → const foo = () => {}
    if node.type in ("lexical_declaration", "variable_declaration"):
        for child in node.children:
            if child.type == "variable_declarator":
                for gc in child.children:
                    if gc.type == "identifier":
                        return _get_text(gc, source)

    # Caso general → busca el primer identifier o property_identifier hijo
    for child in node.children:
        if child.type in ("identifier", "property_identifier", "field_identifier"):
            return _get_text(child, source)

    return "anonymous"


def _extract_signature(node, source: bytes) -> Optional[str]:
    """
    Extrae la firma (parámetros) si el nodo es función/método.
    Retorna None para clases y declaraciones de variables.
    """
    for child in node.children:
        if child.type in ("parameters", "formal_parameters", "parameter_list"):
            raw = _get_text(child, source)
            # Trunca firmas muy largas para no saturar el esqueleto
            return raw if len(raw) <= 120 else raw[:117] + "…)"
    return None


def _extract_decorators(node, source: bytes) -> list[str]:
    """Extrae decoradores Python (@tool, @app.route, etc.)."""
    decorators = []
    if node.type == "decorated_definition":
        for child in node.children:
            if child.type == "decorator":
                decorators.append(_get_text(child, source).strip())
    return decorators


# ─────────────────────────────────────────────────────────────
#  Traversal recursivo con límite de profundidad
# ─────────────────────────────────────────────────────────────

def _extract_skeleton(node, source: bytes, depth: int = 0) -> list[str]:
    if depth > MAX_DEPTH:
        return []

    lines = []

    if node.type in TARGET_NODES:
        indent     = "  " * depth
        name       = _extract_name(node, source)
        signature  = _extract_signature(node, source)
        decorators = _extract_decorators(node, source)
        kind       = node.type.replace("_definition", "").replace("_declaration", "").replace("_", " ").capitalize()
        start_line = node.start_point[0] + 1
        end_line   = node.end_point[0] + 1

        # Decoradores primero
        for dec in decorators:
            lines.append(f"{indent}  {dec}")

        # Línea principal
        sig_str = f"  {signature}" if signature else ""
        lines.append(f"{indent}▸ [{kind}] {name}{sig_str}  (L{start_line}–{end_line})")

        depth += 1   # Hijos con más indentación

    for child in node.children:
        lines.extend(_extract_skeleton(child, source, depth))

    return lines


# ─────────────────────────────────────────────────────────────
#  API pública — la tool de Koda llama esto
# ─────────────────────────────────────────────────────────────

def get_code_skeleton(file_path: str) -> str:
    """
    Parses a source code file and returns its structural skeleton (AST).
    Shows classes, functions, methods, decorators, and signatures with line numbers.
    Useful to understand large files without consuming massive LLM tokens.
    """
    global LANGUAGE_MAP
    if not LANGUAGE_MAP:
        LANGUAGE_MAP = _load_languages()

    if not os.path.exists(file_path):
        return f"Error: File '{file_path}' does not exist."

    _, ext = os.path.splitext(file_path.lower())

    if ext not in LANGUAGE_MAP:
        supported = ", ".join(sorted(LANGUAGE_MAP.keys())) or "none installed"
        return (
            f"Error: AST parsing not supported for '{ext}' files.\n"
            f"Supported: {supported}\n"
            f"Use 'koda_read_file' instead."
        )

    try:
        with open(file_path, "rb") as f:
            source = f.read()

        if len(source) > 500_000:   # 500 KB — archivos gigantes no tiene sentido parsearlos completos
            return f"Error: File '{file_path}' is too large ({len(source)//1024} KB). Split it first."

        from tree_sitter import Parser
        parser = Parser(LANGUAGE_MAP[ext])   # API moderna (≥0.22)
        tree   = parser.parse(source)

        skeleton_lines = _extract_skeleton(tree.root_node, source)

        if not skeleton_lines:
            return f"No classes or functions found in '{file_path}'."

        lang_name = ext.lstrip(".")
        header    = f"=== SKELETON: {file_path} ({lang_name}) — {len(skeleton_lines)} symbols ===\n"
        return header + "\n".join(skeleton_lines)

    except Exception as e:
        return f"Error parsing AST for '{file_path}': {str(e)}"