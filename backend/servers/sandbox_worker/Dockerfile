# Usamos Ubuntu como base para el sandbox
FROM ubuntu:22.04

# Evitar preguntas interactivas
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Python, Git, Curl, Nano
RUN apt-get update && apt-get install -y \
    python3 python3-pip curl git wget nano sudo \
    && rm -rf /var/lib/apt/lists/*

# Instalar Node.js (versión 20)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Carpeta de trabajo
WORKDIR /workspace