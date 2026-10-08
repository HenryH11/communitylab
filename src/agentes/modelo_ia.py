"""Fachada de acceso a proveedores de modelos de IA."""

from pydantic import BaseModel

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_proveedor_analisis,
)
from src.agentes.proveedores.gemini import (
    INTERVALO_REVISION_LIMITADOR,
    MAX_RETRIES_GEMINI,
    MODELO_GEMINI,
    SOLICITUDES_POR_SEGUNDO,
    TAMANO_MAXIMO_LIMITADOR,
    obtener_configuracion_modelo as obtener_configuracion_gemini,
    obtener_modelo_gemini,
    obtener_modelo_gemini_estructurado,
)
from src.agentes.proveedores.nvidia_nim import (
    obtener_configuracion_nvidia,
    obtener_modelo_nvidia,
    obtener_modelo_nvidia_estructurado,
)


def obtener_configuracion_modelo() -> dict:
    """Devuelve la configuración no secreta del proveedor de análisis activo."""
    proveedor = obtener_proveedor_analisis()

    if proveedor == PROVEEDOR_NVIDIA_NIM:
        return obtener_configuracion_nvidia()

    return obtener_configuracion_gemini()


def obtener_modelo_analisis_estructurado(
    esquema: type[BaseModel],
    *,
    proveedor: str | None = None,
):
    """Obtiene el modelo estructurado utilizado para análisis."""
    proveedor_activo = (
        proveedor
        if proveedor is not None
        else obtener_proveedor_analisis()
    )

    return _obtener_modelo_estructurado(
        esquema,
        proveedor=proveedor_activo,
    )

def _obtener_modelo_estructurado(
    esquema: type[BaseModel],
    *,
    proveedor: str,
):
    """Obtiene un modelo estructurado del proveedor indicado."""
    if proveedor == PROVEEDOR_GEMINI:
        return obtener_modelo_gemini_estructurado(
            esquema
        )

    if proveedor == PROVEEDOR_NVIDIA_NIM:
        return obtener_modelo_nvidia_estructurado(
            esquema
        )

    raise ValueError(
        f"Proveedor de IA no soportado: {proveedor}"
    )

def obtener_modelo_generacion_estructurado(
    esquema: type[BaseModel],
    *,
    proveedor: str,
):
    """Obtiene el modelo estructurado utilizado por los generadores."""
    return _obtener_modelo_estructurado(
        esquema,
        proveedor=proveedor,
    )


__all__ = [
    "INTERVALO_REVISION_LIMITADOR",
    "MAX_RETRIES_GEMINI",
    "MODELO_GEMINI",
    "SOLICITUDES_POR_SEGUNDO",
    "TAMANO_MAXIMO_LIMITADOR",
    "obtener_configuracion_modelo",
    "obtener_modelo_analisis_estructurado",
    "obtener_modelo_gemini",
    "obtener_modelo_nvidia",
]