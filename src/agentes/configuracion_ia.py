"""Configuración no secreta de proveedores y modelos de IA."""

import os

from dotenv import load_dotenv
from src.agentes.errores_ia import ErrorConfiguracionProveedor

PROVEEDOR_GEMINI = "gemini"
PROVEEDOR_NVIDIA_NIM = "nvidia_nim"

PROVEEDORES_SOPORTADOS = {
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
}

VARIABLE_PROVEEDOR_ANALISIS = "COMMUNITYLAB_PROVEEDOR_ANALISIS"

VARIABLE_PROVEEDOR_GENERACION = ("COMMUNITYLAB_PROVEEDOR_GENERACION")

VARIABLE_TIMEOUT_NVIDIA = "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS"

TIMEOUT_NVIDIA_POR_DEFECTO = 3.0

PROVEEDOR_GENERACION_POR_DEFECTO = (PROVEEDOR_GEMINI)

PROVEEDOR_ANALISIS_POR_DEFECTO = PROVEEDOR_GEMINI


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

MODELO_NVIDIA_NEMOTRON = (
    "nvidia/nemotron-3.5-lightning-30b-a3b"
)

# Los reintentos los controla la capa de aplicación.
# Evitamos sumar retries ocultos del cliente NVIDIA.
MAX_RETRIES_CLIENTE_NVIDIA = 0


def obtener_proveedor_analisis() -> str:
    """Obtiene y valida el proveedor configurado para análisis."""
    load_dotenv()

    proveedor = os.getenv(
        VARIABLE_PROVEEDOR_ANALISIS,
        PROVEEDOR_ANALISIS_POR_DEFECTO,
    ).strip().lower()

    if proveedor not in PROVEEDORES_SOPORTADOS:
        opciones = ", ".join(
            sorted(PROVEEDORES_SOPORTADOS)
        )
        raise ValueError(
            f"Proveedor de análisis no soportado: {proveedor}. "
            f"Opciones válidas: {opciones}."
        )

    return proveedor


def obtener_proveedor_generacion() -> str:
    """Obtiene y valida el proveedor configurado para generación."""
    load_dotenv()

    proveedor = os.getenv(
        VARIABLE_PROVEEDOR_GENERACION,
        PROVEEDOR_GENERACION_POR_DEFECTO,
    ).strip().lower()

    if proveedor not in PROVEEDORES_SOPORTADOS:
        opciones = ", ".join(
            sorted(PROVEEDORES_SOPORTADOS)
        )
        raise ValueError(
            f"Proveedor de generación no soportado: {proveedor}. "
            f"Opciones válidas: {opciones}."
        )

    return proveedor


def obtener_timeout_nvidia() -> float:
    """Obtiene y valida el timeout configurable de NVIDIA NIM."""
    load_dotenv()

    valor = os.getenv(
        VARIABLE_TIMEOUT_NVIDIA,
        str(TIMEOUT_NVIDIA_POR_DEFECTO),
    ).strip()

    try:
        timeout = float(valor)
    except ValueError as error:
        raise ErrorConfiguracionProveedor(
            f"{VARIABLE_TIMEOUT_NVIDIA} debe ser un número."
        ) from error

    if timeout <= 0:
        raise ErrorConfiguracionProveedor(
            f"{VARIABLE_TIMEOUT_NVIDIA} debe ser mayor que cero."
        )

    return timeout