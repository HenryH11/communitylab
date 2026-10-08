"""Reintentos acotados para llamadas al modelo y registro uniforme de fallos."""

import logging
import random
import re
import time
from collections.abc import Callable
from typing import TypeVar

from langchain_core.exceptions import OutputParserException

from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorFallbackProveedores,
    ErrorSalidaProveedor,
)

from src.agentes.observabilidad import registrar_evento


# Se suma a los reintentos internos del cliente (MAX_RETRIES_GEMINI en modelo_ia.py).
MAX_INTENTOS = 3
ESPERA_BASE_SEGUNDOS = 2.0
ESPERA_MAXIMA_SEGUNDOS = 30.0

_TIPOS_TRANSITORIOS = {
    "TimeoutError",
    "ConnectionError",
    "ResourceExhausted",
    "ServiceUnavailable",
    "DeadlineExceeded",
    "InternalServerError",
    "TooManyRequests",
    "APITimeoutError",
    "APIConnectionError",
}
_CODIGOS_TRANSITORIOS = {429, 500, 502, 503, 504}
_PATRON_TRANSITORIO = re.compile(
    r"\b(429|500|502|503|504)\b|resource[_ ]exhausted|unavailable"
    r"|timed? ?out|deadline|rate limit|temporar",
    re.IGNORECASE,
)

T = TypeVar("T")


class FalloOperacion(Exception):
    """Fallo definitivo tras agotar intentos o ante un error no reintentable."""

    def __init__(self, causa: BaseException, intentos: int, reintentable: bool):
        super().__init__(str(causa))
        self.causa = causa
        self.intentos = intentos
        self.reintentable = reintentable


def es_error_transitorio(error: BaseException) -> bool:
    """Clasifica errores que justifican repetir una llamada al proveedor."""
    if isinstance(error, ErrorConfiguracionProveedor):
        return False
    if isinstance(
        error,
        (ErrorSalidaProveedor, OutputParserException),
    ):
        return True
    if isinstance(error, (TimeoutError, ConnectionError)):
        return True
    if {clase.__name__ for clase in type(error).__mro__} & _TIPOS_TRANSITORIOS:
        return True
    codigo = getattr(error, "code", None) or getattr(error, "status_code", None)
    if codigo in _CODIGOS_TRANSITORIOS:
        return True
    return bool(_PATRON_TRANSITORIO.search(str(error)))


def calcular_espera(intento: int) -> float:
    """Backoff exponencial con jitter para no sincronizar reintentos."""
    tope = min(ESPERA_MAXIMA_SEGUNDOS, ESPERA_BASE_SEGUNDOS * 2 ** (intento - 1))
    return random.uniform(tope / 2, tope)


def _esperar(segundos: float) -> None:
    time.sleep(segundos)


def ejecutar_con_reintentos(
    operacion: Callable[[int], T],
    *,
    contexto: dict,
    max_intentos: int | None = None,
) -> T:
    """Ejecuta `operacion(intento)` y reintenta solo errores transitorios."""
    limite = max_intentos or MAX_INTENTOS

    for intento in range(1, limite + 1):
        try:
            return operacion(intento)
        except Exception as error:
            reintentable = es_error_transitorio(error)
            if reintentable and intento < limite:
                espera = calcular_espera(intento)
                registrar_evento(
                    "reintento_programado",
                    nivel=logging.WARNING,
                    intento=intento,
                    espera_segundos=round(espera, 2),
                    tipo_error=type(error).__name__,
                    mensaje=str(error),
                    **contexto,
                )
                _esperar(espera)
                continue

            registrar_evento(
                "operacion_fallida",
                nivel=logging.ERROR,
                exc_info=error,
                intentos=intento,
                reintentable=reintentable,
                tipo_error=type(error).__name__,
                mensaje=str(error),
                **contexto,
            )
            raise FalloOperacion(error, intento, reintentable) from error

    raise RuntimeError("max_intentos debe ser mayor que cero")


def _causa(error: BaseException) -> BaseException:
    return error.causa if isinstance(error, FalloOperacion) else error


def construir_fallo(
    etapa: str,
    error: BaseException,
    *,
    id_interaccion: str | None = None,
    ruta: str | None = None,
) -> dict:
    """Registro seguro para el contrato de salida; sin traceback."""
    causa = _causa(error)
    fallo: dict[str, object] = {"etapa": etapa}
    if id_interaccion is not None:
        fallo["id"] = id_interaccion
    if ruta is not None:
        fallo["ruta"] = ruta
    fallo.update(
        tipo_error=type(causa).__name__,
        mensaje=str(causa),
        intentos=error.intentos if isinstance(error, FalloOperacion) else 1,
        reintentable=(
            error.reintentable
            if isinstance(error, FalloOperacion)
            else es_error_transitorio(causa)
        ),
    )
    if isinstance(causa, ErrorFallbackProveedores):
        traza = causa.traza

        fallo.update(
            proveedor_primario=traza.get("proveedor_primario"),
            proveedor_respaldo=traza.get("proveedor_usado"),
            fallback_activado=True,
            motivo_fallback=traza.get("motivo_fallback"),
            error_primario=traza.get("error_primario"),
            error_respaldo=traza.get("error_respaldo"),
        )

    return fallo


def describir_error(etapa: str, error: BaseException, ruta: str | None = None) -> str:
    """Texto compatible con la lista histórica `errores`."""
    causa = _causa(error)
    prefijo = f"{etapa}[{ruta}]" if ruta else etapa
    return f"{prefijo}: {type(causa).__name__}: {causa}"
