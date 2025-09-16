# Imagen oficial con Python
FROM python:3.11-slim

# No pedir confirmación en instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias del sistema y ODBC 18
RUN apt-get update && apt-get install -y \
    curl gnupg gcc g++ unixodbc unixodbc-dev \
    libpq-dev libssl-dev libffi-dev libxml2-dev \
    libxslt1-dev libsasl2-dev libldap2-dev \
    libcurl4-openssl-dev \
    libmagic1 file \
    git \
    && mkdir -p /etc/apt/keyrings \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/keyrings/microsoft.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/microsoft.asc] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /app

# Copia todo el proyecto
COPY . .

# Instala paquetes de Python
RUN pip install --upgrade pip && pip install -r requirements.txt

# Puerto (Render lo ignora y pone el suyo vía $PORT)
EXPOSE 10000

# Comando que corre el servidor
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000"]
