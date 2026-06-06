import os

def patch_file_content(file_path: str, search_block: str, replace_block: str) -> str:
    """
    Reemplaza un bloque exacto de código en un archivo.
    Ahorra tokens al no reescribir todo el documento.
    """
    # 1. Validar que el archivo exista
    if not os.path.exists(file_path):
        return f"Error: The file '{file_path}' does not exist. Check the path."

    try:
        # 2. Leer el archivo actual
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. Validar que el bloque de búsqueda exista EXACTAMENTE
        if search_block not in content:
            # Truco pro: Si falla, le damos una pista al LLM de cómo se ve el archivo real
            preview = content[:500] + "\n...[truncated]...\n" if len(content) > 500 else content
            return (
                "Error: 'search_block' not found exactly as written. "
                "Check indentation, line breaks, or spaces. "
                f"Here is a preview of the file:\n{preview}"
            )

        # 4. Reemplazar y guardar
        new_content = content.replace(search_block, replace_block)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        return f"Success: Block replaced successfully in '{file_path}'."
        
    except Exception as e:
        return f"Error patching file: {str(e)}"