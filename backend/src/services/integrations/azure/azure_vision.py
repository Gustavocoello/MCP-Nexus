# src/services/rag/azure_vision.py
import os
import time
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from azure.cognitiveservices.vision.computervision import ComputerVisionClient
from azure.cognitiveservices.vision.computervision.models import VisualFeatureTypes
from msrest.authentication import CognitiveServicesCredentials

from src.database.settings.connection import SessionLocal
from src.database.models import Document
from src.core.time_helper import get_now
from src.core.logging import get_logger

logger = get_logger("azure_vision")

load_dotenv()

# Lógica de las 2 cuentas sumadas
LIMIT_PER_ACCOUNT = 5000
TOTAL_LIMIT = 10000

def analyze_image_with_azure(image_bytes: bytes, user_id: str) -> str:
    """
    Analiza una imagen usando Azure AI Vision.
    Usa un sistema de cascada para balancear 2 cuentas de Azure (5k cada una = 10k total).
    """
    now = get_now()
    first_day_of_month = datetime(now.year, now.month, 1)
    
    session = SessionLocal()
    try:
        # 1. Contar cuántas imágenes van en el mes
        ocr_count = session.query(Document).filter(
            Document.user_id == user_id,
            Document.created_at >= first_day_of_month
        ).count()
        
        # 2. Verificar el límite máximo total (10k)
        if ocr_count >= TOTAL_LIMIT:
            raise ValueError(f"Límite mensual total de OCR alcanzado ({TOTAL_LIMIT} imágenes).")

        # 3. ROTACIÓN DE CUENTAS (El truco maestro)
        if ocr_count < LIMIT_PER_ACCOUNT:
            # De 0 a 4,999 -> Usa Cuenta 1
            endpoint = os.getenv("AZURE_VISION_ENDPOINT_1")
            key = os.getenv("AZURE_KEY1.1")
            cuenta_activa = "Account 1"
        else:
            # De 5,000 a 9,999 -> Usa Cuenta 2
            endpoint = os.getenv("AZURE_VISION_ENDPOINT_2")
            key = os.getenv("AZURE_KEY2.1")
            cuenta_activa = "Account 2"

        if not endpoint or not key:
            raise ValueError(f"Credenciales incompletas en el .env para la {cuenta_activa}")

        logger.info(f"Procesando imagen #{ocr_count + 1} del mes usando {cuenta_activa}")

        # 4. Iniciar Cliente con la cuenta seleccionada
        client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
        stream = BytesIO(image_bytes)
        ocr_number = ocr_count + 1

        # --- Parte 1: Análisis Visual ---
        # --- Parte 1: Análisis Visual (INGLÉS) ---
        analysis = client.analyze_image_in_stream(
            stream,
            visual_features=[VisualFeatureTypes.description,
                             VisualFeatureTypes.color,
                             VisualFeatureTypes.tags]
        )

        description = analysis.description.captions[0].text if analysis.description.captions else "No description available."
        colors = {
            "background": analysis.color.dominant_color_background,
            "foreground": analysis.color.dominant_color_foreground,
            "accent": analysis.color.accent_color
        }
        tags = [tag.name for tag in analysis.tags][:5]

        # Formato limpio y estructurado en inglés para Jarvis/Ragel
        visual_summary = f"""**Visual Analysis of Image #{ocr_number}**
            **Description**: {description}
            **Colors**: Background: {colors['background']}, Foreground: {colors['foreground']}, Accent: #{colors['accent']}
            **Tags**: {', '.join(tags)}
            """

        # --- Parte 2: OCR (INGLÉS) ---
        ocr_stream = BytesIO(image_bytes)
        result = client.read_in_stream(ocr_stream, raw=True)
        operation_location = result.headers["Operation-Location"]
        operation_id = operation_location.split("/")[-1]

        while True:
            read_result = client.get_read_result(operation_id)
            if read_result.status.lower() in ["succeeded", "failed"]:
                break
            time.sleep(0.5)

        if read_result.status.lower() != "succeeded":
            raise ValueError(f"Error processing image with Azure Vision OCR on {cuenta_activa}")

        ocr_lines = []
        for page in read_result.analyze_result.read_results:
            for line in page.lines:
                ocr_lines.append(line.text)

        ocr_text = "\n".join(ocr_lines) if ocr_lines else "No text detected."
        
        # --- Unión final (INGLÉS) ---
        full_context = f"{visual_summary}\n**Extracted OCR Text:**\n{ocr_text}"
        return full_context

    except Exception as e:
        logger.error(f"Error in analyze_image_with_azure: {str(e)}")
        raise e
    finally:
        session.close()
        
        
# ====================== Funcion para extraer texto de imagenes Azure AI Vision - Un solo servicio ========================
OCR_LIMIT = 5000

def analyze_image_with_azure(image_bytes):
    endpoint = AZURE_ENDPOINT
    key = AZURE_KEY

    if not endpoint or not key:
        raise ValueError("Azure Vision endpoint o key no definidos.")

    client = ComputerVisionClient(endpoint, CognitiveServicesCredentials(key))
    stream = BytesIO(image_bytes)

    # --- Control de límite mensual OCR ---
    now = get_now()
    first_day_of_month = datetime(now.year, now.month, 1)
    
    # Contar cuántas imágenes ha subido el usuario este mes
    session = SessionLocal()
    ocr_count = session.query(Document).filter(
        Document.user_id == g.user_id,
        Document.created_at >= first_day_of_month,
        Document.source == "onedrive"  # solo imágenes subidas a OneDrive
    ).count()
    session.close()

    if ocr_count >= OCR_LIMIT:
        raise ValueError("Límite mensual de OCR alcanzado (5000 imágenes).")

    # Asignamos el número OCR incremental
    ocr_number = ocr_count + 1

    # --- Parte 1: Análisis Visual ---
    analysis = client.analyze_image_in_stream(
        stream,
        visual_features=[VisualFeatureTypes.description,
                         VisualFeatureTypes.color,
                         VisualFeatureTypes.tags]
    )

    description = analysis.description.captions[0].text if analysis.description.captions else "Sin descripción."
    colors = {
        "fondo": analysis.color.dominant_color_background,
        "frente": analysis.color.dominant_color_foreground,
        "acentos": analysis.color.accent_color
    }
    tags = [tag.name for tag in analysis.tags][:5]

    visual_summary = f""" **Imagen #{ocr_number}** (proporcionada por usuario)
        **Descripción**: {description}
        **Colores**: Fondo: {colors['fondo']}, Frente: {colors['frente']}, Acento: #{colors['acentos']}
        **Etiquetas**: {', '.join(tags)}
        """

    # --- Parte 2: OCR ---
    ocr_stream = BytesIO(image_bytes)
    result = client.read_in_stream(ocr_stream, raw=True)
    operation_location = result.headers["Operation-Location"]
    operation_id = operation_location.split("/")[-1]

    while True:
        read_result = client.get_read_result(operation_id)
        if read_result.status.lower() in ["succeeded", "failed"]:
            break
        time.sleep(0.5)

    if read_result.status.lower() != "succeeded":
        raise ValueError("Error procesando imagen con Azure Vision OCR")

    ocr_lines = []
    for page in read_result.analyze_result.read_results:
        for line in page.lines:
            ocr_lines.append(line.text)

    ocr_text = "\n".join(ocr_lines) if ocr_lines else "Sin texto detectado."
    
    # --- Unión final ---
    full_context = f"{visual_summary}\n**Texto OCR:**\n{ocr_text}"

    return full_context


def can_upload_image(username: str) -> bool:
    """
    Retorna True si el usuario puede subir imágenes.
    Solo permite usuarios cuyo nombre empieza con 'G' o 'U'.
    """
    if not username:
        return False
    return username.upper().startswith(("G", "U"))
