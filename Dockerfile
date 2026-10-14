# Misma base en ambas etapas para conservar compatibilidad del entorno virtual.
FROM python:3.12-slim AS dependencias
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

# Evitar generación de archivos .pyc y forzar salida en tiempo real
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --create-home appuser && \
    mkdir -p /app/salida/datos /app/salida/logs && \
    chown -R appuser:appuser /app/salida
WORKDIR /app
COPY --from=dependencias /opt/venv /opt/venv
# No copiar el repositorio completo: solo archivos necesarios en ejecución.
COPY src/ ./src/
COPY configuracion/ ./configuracion/
USER appuser

# Puerto estándar de Streamlit
EXPOSE 8501

# Verificación de estado del servicio
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5)" || exit 1

# Comando de arranque del frontend interactivo
CMD ["streamlit", "run", "src/app/app.py"]
