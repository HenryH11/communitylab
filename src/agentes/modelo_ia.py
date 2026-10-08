"""Fachada de acceso a proveedores de modelos de IA."""

from pydantic import BaseModel

from collections.abc import Callable
from typing import Any

from langchain_core.exceptions import OutputParserException

from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorFallbackProveedores,
    ErrorSalidaProveedor,
)
from src.agentes.reintentos import (
    FalloOperacion,
    ejecutar_con_reintentos,
)

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


def _nombre_proveedor(proveedor: Callable) -> str:
    """Obtiene un nombre seguro para trazabilidad."""
    nombre_mock = getattr(proveedor, "_mock_name", None)

    if isinstance(nombre_mock, str) and nombre_mock:
        return nombre_mock

    nombre = getattr(proveedor, "__name__", None)

    if isinstance(nombre, str) and nombre:
        return nombre

    return type(proveedor).__name__.lower()


def _causa_fallo(error: BaseException) -> BaseException:
    """Extrae la causa original si falló la capa de reintentos."""
    if isinstance(error, FalloOperacion):
        return error.causa

    return error


def _motivo_seguro_fallback(error: BaseException) -> str | None:
    """
    Clasifica únicamente errores que justifican cambiar de proveedor.

    Nunca incorpora el mensaje crudo del proveedor.
    """
    causa = _causa_fallo(error)

    if isinstance(causa, ErrorConfiguracionProveedor):
        return "configuracion_proveedor"

    if isinstance(
        causa,
        (ErrorSalidaProveedor, OutputParserException),
    ):
        return "salida_invalida"

    if isinstance(causa, TimeoutError):
        return "timeout"

    if isinstance(causa, ConnectionError):
        return "conexion"

    codigo = (
        getattr(causa, "status_code", None)
        or getattr(causa, "code", None)
    )

    if codigo == 429:
        return "http_429"

    if codigo in {500, 502, 503, 504}:
        return f"http_{codigo}"

    nombres_clases = {
        clase.__name__
        for clase in type(causa).__mro__
    }

    if nombres_clases & {
        "ResourceExhausted",
        "TooManyRequests",
    }:
        return "limite_proveedor"

    if nombres_clases & {
        "APITimeoutError",
        "DeadlineExceeded",
    }:
        return "timeout"

    if nombres_clases & {
        "APIConnectionError",
        "ServiceUnavailable",
    }:
        return "conexion"

    if "InternalServerError" in nombres_clases:
        return "error_servidor"

    return None


def invocar_modelo_con_fallback(
    entrada,
    *,
    primario: Callable,
    respaldo: Callable,
) -> dict[str, Any]:
    """
    Invoca primero el proveedor primario.

    Los errores operativos o una salida inutilizable activan el respaldo
    después de agotar los reintentos aplicables del primario.

    Los errores propios de la entrada se propagan sin activar el respaldo.
    """
    nombre_primario = _nombre_proveedor(primario)
    nombre_respaldo = _nombre_proveedor(respaldo)

    fallo_primario: BaseException | None = None

    try:
        resultado = ejecutar_con_reintentos(
            lambda _intento: primario(entrada),
            contexto={
                "etapa": "proveedor_primario",
                "proveedor": nombre_primario,
            },
        )

        return {
            "resultado": resultado,
            "traza": {
                "proveedor_primario": nombre_primario,
                "proveedor_usado": nombre_primario,
                "fallback_activado": False,
                "motivo_fallback": None,
            },
        }

    except Exception as error_primario:
        fallo_primario = error_primario

        motivo = _motivo_seguro_fallback(
            error_primario
        )

        if motivo is None:
            causa = _causa_fallo(
                error_primario
            )
            raise causa
    try:
        resultado = respaldo(entrada)

        return {
            "resultado": resultado,
            "traza": {
                "proveedor_primario": nombre_primario,
                "proveedor_usado": nombre_respaldo,
                "fallback_activado": True,
                "motivo_fallback": motivo,
            },
        }

    except Exception as error_respaldo:
        assert fallo_primario is not None

        causa_primaria = _causa_fallo(
            fallo_primario
        )

        traza = {
            "proveedor_primario": nombre_primario,
            "proveedor_usado": nombre_respaldo,
            "fallback_activado": True,
            "motivo_fallback": motivo,
            "error_primario": {
                "tipo": type(causa_primaria).__name__,
                "motivo": motivo,
            },
            "error_respaldo": {
                "tipo": type(error_respaldo).__name__,
            },
        }

        raise ErrorFallbackProveedores(
            traza
        ) from error_respaldo


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