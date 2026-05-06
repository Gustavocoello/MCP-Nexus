FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instalación de dependencias del sistema (Drivers ODBC, etc.)
RUN apt-get update && apt-get install -y \
    curl gnupg git gcc g++ unixodbc unixodbc-dev \
    libpq-dev libssl-dev libffi-dev libxml2-dev \
    libxslt1-dev libsasl2-dev libldap2-dev \
    libcurl4-openssl-dev \
    libmagic1 file \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiamos los archivos de la carpeta actual (Notion o Calendar)
# Al estar el Dockerfile dentro, "." se refiere a la carpeta del servidor
COPY . .

# Instalamos las dependencias específicas
RUN pip install --upgrade pip && \
    if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

# Definimos el PYTHONPATH para que Python encuentre los subdirectorios
ENV PYTHONPATH="/app"

# Comando de inicio (ajusta el nombre del archivo según la carpeta)
CMD ["python", "notion_server.py"]