"""Logging estructurado y callbacks de LangChain para Ciencia de Datos."""

import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.runnables import RunnableConfig


RAIZ = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger("communitylab.ciencia_datos")
NOMBRE_ARCHIVO_LOG = "ciencia_datos.jsonl"
_CAMPOS_METADATA = ("etapa", "intento", "id_interaccion", "ids_interaccion", "ruta")
_CAMPOS_TOKENS = ("input_tokens", "output_tokens", "total_tokens")

_id_ejecucion: ContextVar[str | None] = ContextVar("id_ejecucion", default=None)
_ruta_log: Path | None = None
_bloqueo_configuracion = threading.Lock()


class FormateadorJson(logging.Formatter):
    """Una línea JSON por evento; el traceback solo se incluye en el log técnico."""

    def format(self, record: logging.LogRecord) -> str:
        datos = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "nivel": record.levelname,
            "evento": getattr(record, "evento", record.getMessage()),
        }
        id_ejecucion = getattr(record, "id_ejecucion", None)
        if id_ejecucion:
            datos["id_ejecucion"] = id_ejecucion
        datos.update(getattr(record, "campos", {}))
        if record.exc_info:
            datos["traceback"] = self.formatException(record.exc_info)
        return json.dumps(datos, ensure_ascii=False, default=str)


def registrar_evento(
    evento: str,
    *,
    nivel: int = logging.INFO,
    exc_info: BaseException | None = None,
    **campos,
) -> None:
    LOGGER.log(
        nivel,
        evento,
        exc_info=exc_info,
        extra={
            "evento": evento,
            "campos": campos,
            "id_ejecucion": _id_ejecucion.get(),
        },
    )


def configurar_logging() -> Path | None:
    """Activa el archivo JSONL de logs una sola vez; COMMUNITYLAB_LOGS=0 lo desactiva."""
    global _ruta_log

    if os.getenv("COMMUNITYLAB_LOGS", "1").strip().lower() in {"0", "false", "no"}:
        return None

    with _bloqueo_configuracion:
        if _ruta_log is not None:
            return _ruta_log

        directorio = Path(
            os.getenv("COMMUNITYLAB_LOG_DIR") or RAIZ / "salida" / "logs"
        )
        directorio.mkdir(parents=True, exist_ok=True)
        ruta = directorio / NOMBRE_ARCHIVO_LOG

        manejador = logging.FileHandler(ruta, encoding="utf-8")
        manejador.setFormatter(FormateadorJson())
        LOGGER.addHandler(manejador)
        LOGGER.setLevel(os.getenv("COMMUNITYLAB_LOG_LEVEL", "INFO").upper())
        _ruta_log = ruta
        return ruta


@contextmanager
def contexto_ejecucion(id_ejecucion: str | None = None):
    """Asocia todos los eventos del bloque a un mismo ID de ejecución."""
    identificador = id_ejecucion or uuid.uuid4().hex
    token = _id_ejecucion.set(identificador)
    try:
        yield identificador
    finally:
        _id_ejecucion.reset(token)


def _contexto_desde_metadata(metadata: dict | None) -> dict:
    metadata = metadata or {}
    contexto = {
        campo: metadata[campo]
        for campo in _CAMPOS_METADATA
        if metadata.get(campo) is not None
    }
    if metadata.get("ls_model_name"):
        contexto["modelo"] = metadata["ls_model_name"]
    return contexto


def _uso_tokens(respuesta) -> dict | None:
    for generaciones in getattr(respuesta, "generations", None) or []:
        for generacion in generaciones:
            mensaje = getattr(generacion, "message", None)
            uso = getattr(mensaje, "usage_metadata", None)
            if uso:
                return {campo: uso[campo] for campo in _CAMPOS_TOKENS if campo in uso}

    salida = getattr(respuesta, "llm_output", None) or {}
    uso = salida.get("usage_metadata") or salida.get("token_usage")
    if uso:
        return {campo: uso[campo] for campo in _CAMPOS_TOKENS if campo in uso}
    return None


class ManejadorObservabilidad(BaseCallbackHandler):
    """Registra inicio, fin, duración, tokens y errores de cada llamada al modelo."""

    def __init__(self) -> None:
        self._inicios: dict = {}
        self._bloqueo = threading.Lock()

    def _iniciar(self, run_id, metadata, cantidad_mensajes: int) -> None:
        contexto = _contexto_desde_metadata(metadata)
        with self._bloqueo:
            self._inicios[run_id] = (time.perf_counter(), contexto)
        registrar_evento(
            "llm_inicio",
            nivel=logging.DEBUG,
            run_id=str(run_id),
            cantidad_mensajes=cantidad_mensajes,
            **contexto,
        )

    def _finalizar(self, run_id) -> tuple[float | None, dict]:
        with self._bloqueo:
            inicio, contexto = self._inicios.pop(run_id, (None, {}))
        if inicio is None:
            return None, contexto
        return round((time.perf_counter() - inicio) * 1000, 1), contexto

    def on_chat_model_start(
        self, _serialized, messages, *, run_id, metadata=None, **_kwargs
    ):
        del _serialized, _kwargs
        self._iniciar(run_id, metadata, sum(len(grupo) for grupo in messages))

    def on_llm_start(
        self, _serialized, prompts, *, run_id, metadata=None, **_kwargs
    ):
        del _serialized, _kwargs
        self._iniciar(run_id, metadata, len(prompts))

    def on_llm_end(self, response, *, run_id, **_kwargs):
        del _kwargs
        duracion_ms, contexto = self._finalizar(run_id)
        registrar_evento(
            "llm_fin",
            run_id=str(run_id),
            duracion_ms=duracion_ms,
            uso_tokens=_uso_tokens(response),
            **contexto,
        )

    def on_llm_error(self, error, *, run_id, **_kwargs):
        del _kwargs
        duracion_ms, contexto = self._finalizar(run_id)
        registrar_evento(
            "llm_error",
            nivel=logging.WARNING,
            run_id=str(run_id),
            duracion_ms=duracion_ms,
            tipo_error=type(error).__name__,
            mensaje=str(error),
            **contexto,
        )


MANEJADOR_OBSERVABILIDAD = ManejadorObservabilidad()


def config_ejecucion(
    etapa: str,
    *,
    intento: int,
    id_interaccion: str | None = None,
    ids_interaccion: list[str] | None = None,
    ruta: str | None = None,
) -> RunnableConfig:
    """Config de LangChain con callback y metadatos para correlacionar logs."""
    metadata: dict[str, object] = {"etapa": etapa, "intento": intento}
    if id_interaccion is not None:
        metadata["id_interaccion"] = id_interaccion
    if ids_interaccion is not None:
        metadata["ids_interaccion"] = list(ids_interaccion)
    if ruta is not None:
        metadata["ruta"] = ruta

    return {
        "callbacks": [MANEJADOR_OBSERVABILIDAD],
        "metadata": metadata,
        "tags": ["communitylab", etapa],
        "run_name": f"{etapa}:{ruta}" if ruta else etapa,
    }
