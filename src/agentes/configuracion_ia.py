"""Configuración no secreta de proveedores y modelos de IA."""

PROVEEDOR_GEMINI = "gemini"
PROVEEDOR_NVIDIA_NIM = "nvidia_nim"

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

MODELO_NVIDIA_NEMOTRON = (
    "nvidia/nemotron-3.5-lightning-30b-a3b"
)

# Los reintentos los controla la capa de aplicación.
# Evitamos sumar retries ocultos del cliente.
MAX_RETRIES_CLIENTE_NVIDIA = 0