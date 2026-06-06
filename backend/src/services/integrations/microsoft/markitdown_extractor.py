# src/services/integrations/microsoft/markitdown_extractor.py
import os
import tempfile
from markitdown import MarkItDown
from src.core.logging import get_logger

logger = get_logger("markitdown_extractor")

def extract_text_from_file(file_stream, filename: str) -> str:
    """
    Extrae texto de archivos (PDF, DOCX, XLSX, PPTX, etc.) usando MarkItDown de Microsoft.
    Devuelve el contenido maravillosamente formateado en Markdown, ideal para LLMs.
    """
    # 1. Identificamos la extensión del archivo original
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    
    logger.info(f"Iniciando extracción con MarkItDown para: {filename} (Ext: {ext})")

    # 2. Inicializamos la herramienta de Microsoft
    md = MarkItDown()

    # 3. Guardamos el stream temporalmente en disco. 
    # MarkItDown funciona mucho mejor leyendo rutas físicas dependiendo del tipo de archivo.
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(file_stream.read())
        temp_path = temp_file.name

    try:
        # 4. Magia pura: Convertimos el documento entero a Markdown
        result = md.convert(temp_path)
        markdown_text = result.text_content
        
        logger.info(f"Extracción exitosa. {filename} convertido a Markdown ({len(markdown_text)} caracteres).")
        
        return markdown_text

    except Exception as e:
        logger.error(f"Error extrayendo {filename} con MarkItDown: {str(e)}")
        raise ValueError(f"No se pudo extraer el texto de {filename}. Formato posiblemente no soportado o corrupto.")
    
    finally:
        # 5. Siempre limpiamos el archivo temporal para no llenar el servidor
        if os.path.exists(temp_path):
            os.remove(temp_path)
