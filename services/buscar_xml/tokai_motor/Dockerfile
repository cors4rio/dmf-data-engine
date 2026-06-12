# Dockerfile - Padrao Senior para Podman/Docker
# Usamos a imagem oficial do Playwright Microsoft que já possui as libs base do Chromium nativas do Linux.
FROM mcr.microsoft.com/playwright/python:v1.42.0-jammy

# Reduz logs excessivos e forca o output do python direto no console
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV HEADLESS_MODE=True

# Instalar utilitarios de descompactacao universais para o Linux (zip e rar)
RUN apt-get update && apt-get install -y \
    unzip \
    p7zip-full \
    unrar \
    && rm -rf /var/lib/apt/lists/*

# Definir Diretorio de Trabalho
WORKDIR /app

# Copiar os requerimentos primeiro para cache de camada no Podman
COPY requirements.txt .

# Atualizar o pip e instalar as dependencias do Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Como já usamos a imagem base do Playwright, nao precisamos de playwright install --with-deps, 
# mas se quisermos apenas garantir a instalacao do binario chromium do pacote pip:
RUN playwright install chromium

# Copiar todo o codigo fonte do bot, a configuracao de credenciais e o mapa
COPY . .

# Comando de execucao padrao do Robo
CMD ["python", "main.py"]
