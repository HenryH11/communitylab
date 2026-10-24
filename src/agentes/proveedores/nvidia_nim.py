"""Proveedor NVIDIA NIM para el pipeline de Ciencia de Datos."""

import os
import json
from functools import lru_cache
from typing import Any

from langchain_core.messages import SystemMessage
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from pydantic import BaseModel, SecretStr, ValidationError

from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorSalidaProveedor,
)

from src.agentes.configuracion_ia import (
    MAX_RETRIES_CLIENTE_NVIDIA,
    NVIDIA_BASE_URL,
    obtener_modelo_nvidia_id,
    obtener_timeout_nvidia,
)


def obtener_configuracion_nvidia() -> dict[str, str | int]:
    """Devuelve configuración no secreta del proveedor NVIDIA NIM."""
    return {
        "proveedor": "NVIDIA NIM",
        "identificador_modelo": obtener_modelo_nvidia_id(),
        "base_url": NVIDIA_BASE_URL,
        "max_retries": MAX_RETRIES_CLIENTE_NVIDIA,
    }


@lru_cache(maxsize=32)
def obtener_modelo_nvidia(
    modelo: str | None = None,
    temperatura: float = 0,
    top_p: float | None = None,
) -> ChatOpenAI:
    """Construye el cliente NVIDIA NIM usando su API OpenAI-compatible."""
    load_dotenv()

    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        raise ErrorConfiguracionProveedor(
            "No se encontró NVIDIA_API_KEY."
        )

    modelo_id = modelo or obtener_modelo_nvidia_id()

    extra_body = None
    if "nemotron" in modelo_id.lower():
        extra_body = {
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        }

    muestreo: dict[str, Any] = {"top_p": top_p} if top_p is not None else {}

    return ChatOpenAI(
        api_key=SecretStr(api_key),
        base_url=NVIDIA_BASE_URL,
        model=modelo_id,
        temperature=temperatura,
        timeout=obtener_timeout_nvidia(),
        max_retries=MAX_RETRIES_CLIENTE_NVIDIA,
        extra_body=extra_body,
        **muestreo,
    )


def _agregar_instruccion_esquema(
    entrada,
    esquema: type[BaseModel],
):
    """
    Añade únicamente instrucciones técnicas de formato para NVIDIA NIM.

    No modifica las reglas semánticas del prompt de CommunityLab.
    """
    if hasattr(entrada, "to_messages"):
        mensajes = list(
            entrada.to_messages()
        )
    elif isinstance(entrada, list):
        mensajes = list(entrada)
    else:
        raise TypeError(
            "Formato de entrada no compatible con NVIDIA NIM"
        )

    esquema_json = json.dumps(
        esquema.model_json_schema(),
        ensure_ascii=False,
    )

    instruccion = SystemMessage(
        content=(
            "REQUISITO TÉCNICO DE SALIDA JSON:\n"
            "Devuelve únicamente un objeto JSON válido que cumpla "
            "exactamente el siguiente JSON Schema.\n\n"
            f"{esquema_json}\n\n"
            "Respeta exactamente los nombres y niveles de las "
            "propiedades definidos por el esquema. "
            "No utilices IDs, categorías ni valores como claves "
            "alternativas del objeto raíz. "
            "No añadas texto fuera del JSON."
        )
    )

    # Conserva primero el system prompt semántico de CommunityLab
    # y coloca después la adaptación técnica del proveedor.
    if mensajes and getattr(
        mensajes[0],
        "type",
        None,
    ) == "system":
        return [
            mensajes[0],
            instruccion,
            *mensajes[1:],
        ]

    return [
        instruccion,
        *mensajes,
    ]


def obtener_modelo_nvidia_estructurado(
    esquema: type[BaseModel],
    *,
    modelo: str | None = None,
    temperatura: float | None = None,
    top_p: float | None = None,
):
    """
    Adapta NVIDIA NIM al contrato estructurado solicitado.

    NVIDIA trabaja en JSON mode y recibe explícitamente el
    JSON Schema correspondiente. Pydantic realiza la validación final.
    `temperatura` y `top_p` solo se envían cuando se indican; si no, el
    cliente conserva su configuración determinista.
    """
    muestreo: dict[str, Any] = {}
    if temperatura is not None:
        muestreo["temperatura"] = temperatura
    if top_p is not None:
        muestreo["top_p"] = top_p
    try:
        cliente_base = (
            obtener_modelo_nvidia(modelo=modelo, **muestreo)
            if modelo is not None or muestreo
            else obtener_modelo_nvidia()
        )
    except TypeError:
        cliente_base = obtener_modelo_nvidia()

    parametros: dict[str, Any] = {
        "response_format": {
            "type": "json_object",
        }
    }

    modelo_efectivo = modelo or getattr(
        cliente_base,
        "model_name",
        None,
    )

    if (
        modelo_efectivo == "nvidia/nemotron-3.5-super-vl-120b-a12b"
        and esquema.__name__ == "SugerenciaPreguntasFrecuentes"
    ):
        parametros["max_tokens"] = 512

    modelo_json = cliente_base.bind(**parametros)

    def preparar_entrada(entrada):
        return _agregar_instruccion_esquema(
            entrada,
            esquema,
        )

    def validar_respuesta(respuesta):
        contenido = respuesta.content

        if not isinstance(contenido, str):
            raise ErrorSalidaProveedor(
                "NVIDIA NIM devolvió contenido no textual."
            )

        if not contenido.strip():
            raise ErrorSalidaProveedor(
                "NVIDIA NIM devolvió una respuesta vacía."
            )

        try:
            return esquema.model_validate_json(
                contenido
            )
        except ValidationError as error:
            raise ErrorSalidaProveedor(
                "NVIDIA NIM devolvió una salida que no cumple el esquema."
            ) from error

    return (
        RunnableLambda(preparar_entrada)
        | modelo_json
        | RunnableLambda(validar_respuesta)
    )
