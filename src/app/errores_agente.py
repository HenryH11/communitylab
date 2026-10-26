"""Traduce fallos del agente a mensajes comprensibles para quien usa la app.

Los mensajes nunca mencionan código, archivos ni configuración interna: explican
qué pasó y qué puede hacer la persona (reintentar o avisar al administrador).
"""

from __future__ import annotations

from src.agentes.interpretacion import ErrorInterpretacion

_AVISAR = "Si el problema continúa, avisa al administrador de CommunityLab."

_ERRORES_DE_CONEXION = {
    "APIConnectionError",
    "APITimeoutError",
    "ConnectError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
    "TimeoutException",
    "OperationalError",
    "InterfaceError",
}


def _cadena_de_causas(error: BaseException):
    vistos: set[int] = set()
    actual: BaseException | None = error
    while actual is not None and id(actual) not in vistos:
        vistos.add(id(actual))
        yield actual
        actual = actual.__cause__ or actual.__context__


def explicar_error(error: BaseException) -> str:
    """Devuelve un mensaje claro y accionable para un fallo al consultar."""
    if isinstance(error, ErrorInterpretacion):
        return str(error)
    if isinstance(error, ValueError):
        return str(error)

    for causa in _cadena_de_causas(error):
        codigo = getattr(causa, "status_code", None)
        if codigo == 404:
            return (
                "El modelo de IA no está disponible en este momento. "
                f"Intenta de nuevo más tarde. {_AVISAR}"
            )
        if codigo in {401, 403}:
            return f"El servicio de IA rechazó el acceso de CommunityLab. {_AVISAR}"
        if codigo == 429:
            return (
                "El servicio de IA alcanzó su límite de uso. "
                "Espera unos minutos e inténtalo de nuevo."
            )
        if isinstance(codigo, int) and codigo >= 500:
            return (
                "El servicio de IA tiene problemas en este momento. "
                "Inténtalo de nuevo en unos minutos."
            )
        if isinstance(causa, (ConnectionError, TimeoutError)) or (
            type(causa).__name__ in _ERRORES_DE_CONEXION
        ):
            return (
                "No hay conexión con el servicio de IA o con la fuente de datos. "
                f"Revisa tu conexión a internet e inténtalo de nuevo. {_AVISAR}"
            )

    return f"Ocurrió un problema inesperado al consultar al agente. {_AVISAR}"
