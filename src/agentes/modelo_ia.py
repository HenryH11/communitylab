"""Fachada de acceso a proveedores de modelos de IA.

Mantiene la API histórica de Gemini mientras la implementación concreta
vive en src.agentes.proveedores.gemini.
"""

from src.agentes.proveedores.gemini import (
    INTERVALO_REVISION_LIMITADOR,
    MAX_RETRIES_GEMINI,
    MODELO_GEMINI,
    SOLICITUDES_POR_SEGUNDO,
    TAMANO_MAXIMO_LIMITADOR,
    obtener_configuracion_modelo,
    obtener_modelo_gemini,
)


__all__ = [
    "INTERVALO_REVISION_LIMITADOR",
    "MAX_RETRIES_GEMINI",
    "MODELO_GEMINI",
    "SOLICITUDES_POR_SEGUNDO",
    "TAMANO_MAXIMO_LIMITADOR",
    "obtener_configuracion_modelo",
    "obtener_modelo_gemini",
]