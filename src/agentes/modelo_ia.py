"""Fachada de acceso a proveedores de modelos de IA."""

from typing import Any

from pydantic import BaseModel
from langchain_core.runnables import RunnableLambda

from src.agentes.consumo import reservar_intento

from src.agentes.fallback_ia import (
    invocar_modelo_con_fallback,
)

from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorFallbackProveedores,
)

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    TIER_ESTANDAR,
    enrutamiento_adaptativo_activo,
    obtener_modelo_nvidia_por_ruta,
    obtener_modelo_nvidia_por_tier,
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
    ruta: str | None = None,
    modelo: str | None = None,
):
    """Obtiene el modelo estructurado utilizado para análisis."""
    proveedor_activo = (
        proveedor
        if proveedor is not None
        else obtener_proveedor_analisis()
    )

    modelo_resuelto = modelo
    if (
        modelo_resuelto is None
        and ruta is not None
        and proveedor_activo == PROVEEDOR_NVIDIA_NIM
        and enrutamiento_adaptativo_activo()
    ):
        modelo_resuelto = obtener_modelo_nvidia_por_tier(TIER_ESTANDAR)

    return _obtener_modelo_estructurado(
        esquema,
        proveedor=proveedor_activo,
        modelo=modelo_resuelto,
    )


def _obtener_modelo_estructurado(
    esquema: type[BaseModel],
    *,
    proveedor: str,
    modelo: str | None = None,
    temperatura: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
):
    """Obtiene un modelo estructurado del proveedor indicado."""
    # Solo se reenvían los parámetros indicados para no romper adaptadores
    # que no aceptan muestreo.
    extras: dict[str, Any] = {
        clave: valor
        for clave, valor in (
            ("modelo", modelo),
            ("temperatura", temperatura),
            ("top_p", top_p),
            ("max_tokens", max_tokens),
        )
        if valor is not None
    }
    if proveedor == PROVEEDOR_GEMINI:
        cadena = obtener_modelo_gemini_estructurado(esquema, **extras)
    elif proveedor == PROVEEDOR_NVIDIA_NIM:
        cadena = obtener_modelo_nvidia_estructurado(esquema, **extras)
    else:
        raise ValueError(f"Proveedor de IA no soportado: {proveedor}")
    if max_tokens is None:
        return cadena

    def autorizar(entrada):
        reservar_intento(entrada, esquema.model_json_schema(), max_tokens)
        return entrada

    return RunnableLambda(autorizar) | cadena


def obtener_modelo_generacion_estructurado(
    esquema: type[BaseModel],
    *,
    proveedor: str,
    ruta: str | None = None,
    modelo: str | None = None,
    temperatura: float | None = None,
    top_p: float | None = None,
    max_tokens: int | None = None,
):
    """Obtiene el modelo estructurado utilizado por los generadores."""
    modelo_resuelto = modelo
    if (
        modelo_resuelto is None
        and ruta is not None
        and proveedor == PROVEEDOR_NVIDIA_NIM
        and enrutamiento_adaptativo_activo()
    ):
        modelo_resuelto = obtener_modelo_nvidia_por_ruta(ruta)

    return _obtener_modelo_estructurado(
        esquema,
        proveedor=proveedor,
        modelo=modelo_resuelto,
        temperatura=temperatura,
        top_p=top_p,
        max_tokens=max_tokens,
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
    "ErrorConfiguracionProveedor",
    "ErrorFallbackProveedores",
    "invocar_modelo_con_fallback",
]
