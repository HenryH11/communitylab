# Imagen base ligera con Python 3.12
FROM python:3.12-slim

# Evitar generación de archivos .pyc y forzar salida en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Instalar dependencias del sistema mínimas necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar manifiesto de dependencias e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente del proyecto
COPY . /app

# Crear carpetas de salida si no existen
RUN mkdir -p /app/salida/datos /app/salida/logs

# Puerto estándar de Streamlit
EXPOSE 8501

# Verificación de estado del servicio
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Comando de arranque del frontend interactivo
CMD ["streamlit", "run", "src/app/app.py"]
