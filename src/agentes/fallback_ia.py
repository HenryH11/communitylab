"""Política de fallback entre proveedores de IA."""

from collections.abc import Callable
from typing import Any

from langchain_core.exceptions import OutputParserException

from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorFallbackProveedores,
    ErrorSalidaProveedor,
)
from src.agentes.observabilidad import obtener_contexto_llamada_ia
from src.agentes.reintentos import (
    FalloOperacion,
    ejecutar_con_reintentos,
    es_error_transitorio,
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


def _motivo_seguro_fallback(
    error: BaseException,
) -> str | None:
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

    if codigo == 400:
        detalle = getattr(causa, "body", None)
        texto_error = str(
            detalle if detalle is not None else causa
        ).upper()

        if (
            "DEGRADED" in texto_error
            and "FUNCTION" in texto_error
        ):
            return "servicio_degradado"

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

    contexto_reintento = {
        **obtener_contexto_llamada_ia(),
        "etapa": "proveedor_primario",
        "proveedor": nombre_primario,
    }

    fallo_primario: BaseException | None = None

    try:
        resultado = ejecutar_con_reintentos(
            lambda _intento: primario(entrada),
            contexto=contexto_reintento,
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

        causa_respaldo = _causa_fallo(
            error_respaldo
        )

        reintentable = (
            es_error_transitorio(causa_primaria)
            or es_error_transitorio(causa_respaldo)
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
            traza,
            reintentable=reintentable,
        ) from error_respaldo
