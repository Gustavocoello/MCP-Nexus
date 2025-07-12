FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive

# Instala dependencias necesarias (como en el otro Dockerfile)
RUN apt-get update && apt-get install -y \
    curl gnupg gcc g++ unixodbc unixodbc-dev \
    libpq-dev libssl-dev libffi-dev libxml2-dev \
    libxslt1-dev libsasl2-dev libldap2-dev \
    libcurl4-openssl-dev \
    libmagic1 file \
    && mkdir -p /etc/apt/keyrings \
    && curl -sSL https://packages.microsoft.com/keys/microsoft.asc -o /etc/apt/keyrings/microsoft.asc \
    && echo "deb [signed-by=/etc/apt/keyrings/microsoft.asc] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiamos todo el backend
COPY ../../.. .

RUN pip install --upgrade pip && pip install -r requirements.txt

# Calendar Server normalmente no expone puertos
CMD ["python", "src/mcps/server/calendar_server.py"]
