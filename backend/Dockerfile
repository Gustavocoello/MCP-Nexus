# Imagen oficial con Python
FROM python:3.11-slim

# No pedir confirmación en instalación
ENV DEBIAN_FRONTEND=noninteractive

# 1. Instala dependencias del sistema, Node.js (para npx) y herramientas básicas
RUN apt-get update && apt-get install -y \
    curl gnupg gcc g++ unixodbc unixodbc-dev \
    libpq-dev libssl-dev libffi-dev libxml2-dev \
    libxslt1-dev libsasl2-dev libldap2-dev \
    libcurl4-openssl-dev \
    libmagic1 file git wget \
    && mkdir -p /etc/apt/keyrings \
    # Llave de Microsoft ODBC
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/keyrings/microsoft.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/microsoft.asc] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    # Instalar Node.js (Requerido para que npx funcione con el MCP)
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y nodejs msodbcsql18 \
    # Limpieza
    && rm -rf /var/lib/apt/lists/*

# 2. Instala Google Chrome estable para Linux
RUN curl -fsSL https://dl.ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copia todo el proyecto
COPY . .

# Instala paquetes de Python
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN playwright install chromium --with-deps

# Render define automáticamente la variable $PORT
ENV PORT=10000

# Definimos la variable de entorno para que el MCP sepa dónde buscar Chrome
ENV CHROME_DEBUG_URL=http://127.0.0.1:9222

# Expone los puertos (el de FastAPI y el de Chrome Debugging)
EXPOSE $PORT
EXPOSE 9222

# Levanta Chrome Headless en background y luego inicia FastAPI con Uvicorn
# Las flags --no-sandbox y --disable-dev-shm-usage son OBLIGATORIAS en Docker
CMD ["bash", "-c", "google-chrome-stable --headless --disable-gpu --no-sandbox --disable-dev-shm-usage --remote-debugging-port=9222 & uvicorn main:app --host 0.0.0.0 --port $PORT"]