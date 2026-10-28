"""Admisión y presupuesto compartido de las consultas en esta instancia."""

from collections import deque
from contextvars import ContextVar
from dataclasses import dataclass
from functools import wraps
import os
from threading import Lock
from time import monotonic

from dotenv import load_dotenv

from src.agentes.contexto import estimar_tokens, obtener_presupuesto_contexto
from src.agentes.errores_ia import ErrorConfiguracionProveedor


class LimiteConsumo(ValueError):
    """Se detiene el trabajo antes de exceder el presupuesto autorizado."""


@dataclass
class ConsumoConsulta:
    max_intentos: int
    max_tokens: int
    intentos: int = 0
    tokens_reservados: int = 0


_actual: ContextVar[ConsumoConsulta | None] = ContextVar("consumo_consulta", default=None)
_lock = Lock()
_activas = 0
_intentos_hora: deque[float] = deque()


def _entero(variable: str, defecto: int, minimo: int = 1) -> int:
    try:
        valor = int(os.getenv(variable, str(defecto)))
    except ValueError as error:
        raise ErrorConfiguracionProveedor(f"{variable} debe ser un entero >= {minimo}.") from error
    if valor < minimo:
        raise ErrorConfiguracionProveedor(f"{variable} debe ser un entero >= {minimo}.")
    return valor


def limitar_consulta(funcion):
    @wraps(funcion)
    def ejecutar(*args, **kwargs):
        global _activas
        load_dotenv()
        consumo = ConsumoConsulta(
            _entero("COMMUNITYLAB_MAX_INTENTOS_CONSULTA", 30),
            _entero("COMMUNITYLAB_MAX_TOKENS_CONSULTA", 250000),
        )
        concurrencia = _entero("COMMUNITYLAB_MAX_CONSULTAS_ACTIVAS", 2)
        _entero("COMMUNITYLAB_MAX_INTENTOS_HORA", 0, 0)
        with _lock:
            if _activas >= concurrencia:
                raise LimiteConsumo("El servicio está ocupado. Espera un momento y vuelve a intentarlo.")
            _activas += 1
        token = _actual.set(consumo)
        try:
            resultado = funcion(*args, **kwargs)
            resultado["consumo"] = {
                "intentos_proveedor": consumo.intentos,
                "tokens_reservados_estimados": consumo.tokens_reservados,
                "max_intentos": consumo.max_intentos,
                "max_tokens": consumo.max_tokens,
            }
            return resultado
        finally:
            _actual.reset(token)
            with _lock:
                _activas -= 1
    return ejecutar


def estimar_entrada(entrada, esquema: dict) -> int:
    mensajes = entrada.to_messages() if hasattr(entrada, "to_messages") else entrada
    contenido = [
        {"rol": getattr(m, "type", ""), "contenido": getattr(m, "content", str(m))}
        for m in mensajes
    ] if isinstance(mensajes, list) else str(mensajes)
    return estimar_tokens(contenido) + estimar_tokens(esquema) + 2048


def reservar_intento(entrada, esquema: dict, salida: int) -> None:
    consumo = _actual.get()
    if consumo is None:
        return
    tokens_entrada = estimar_entrada(entrada, esquema)
    if tokens_entrada + salida > obtener_presupuesto_contexto().total:
        raise LimiteConsumo("La llamada excede el presupuesto de contexto. No se envió al proveedor.")
    reserva = tokens_entrada + salida
    cuota = _entero("COMMUNITYLAB_MAX_INTENTOS_HORA", 0, 0)
    with _lock:
        ahora = monotonic()
        while _intentos_hora and _intentos_hora[0] <= ahora - 3600:
            _intentos_hora.popleft()
        if consumo.intentos >= consumo.max_intentos or consumo.tokens_reservados + reserva > consumo.max_tokens:
            raise LimiteConsumo(
                "Esta consulta alcanzó su presupuesto de procesamiento. "
                "No se guardó una respuesta parcial. Acota la solicitud e inténtalo de nuevo."
            )
        if cuota and len(_intentos_hora) >= cuota:
            raise LimiteConsumo("El servicio alcanzó su cuota horaria compartida. Inténtalo más tarde.")
        consumo.intentos += 1
        consumo.tokens_reservados += reserva
        _intentos_hora.append(ahora)
