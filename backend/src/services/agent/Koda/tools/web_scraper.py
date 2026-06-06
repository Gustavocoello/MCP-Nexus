import requests
from bs4 import BeautifulSoup

def scrape_technical_doc(url: str) -> str:
    """
    Lee una URL específica y extrae su contenido técnico (texto y bloques de código).
    Ignora navbars, footers y scripts para ahorrar tokens.
    """
    try:
        # Usamos un User-Agent realista para que páginas como GitHub o Stripe no nos bloqueen
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return f"Error: Could not access the URL. HTTP Status Code: {response.status_code}"

        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Eliminar basura (scripts, estilos, navbars, footers, headers)
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
            element.decompose()

        # 2. Buscar el contenedor principal (donde suele estar la documentación)
        main_content = soup.find('main') or soup.find('article') or soup.body

        if not main_content:
            return "Error: Could not extract the main content from this page."

        # 3. Extraer el texto limpiando los saltos de línea extra
        text = main_content.get_text(separator='\n')
        
        # Limpiar líneas vacías excesivas
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        # 4. Truncar si es absurdamente largo (límite de seguridad de tokens)
        max_chars = 15000 
        if len(clean_text) > max_chars:
            clean_text = clean_text[:max_chars] + "\n\n...[Content truncated due to length]..."

        return f"Document Content from {url}:\n\n{clean_text}"

    except requests.Timeout:
        return f"Error: The website {url} took too long to respond."
    except Exception as e:
        return f"Error scraping the website: {str(e)}"