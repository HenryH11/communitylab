"""Proveedor NVIDIA NIM para el pipeline de Ciencia de Datos."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.agentes.configuracion_ia import (
    MAX_RETRIES_CLIENTE_NVIDIA,
    MODELO_NVIDIA_NEMOTRON,
    NVIDIA_BASE_URL,
)


def obtener_configuracion_nvidia() -> dict[str, str | int]:
    """Devuelve configuración no secreta del proveedor NVIDIA NIM."""
    return {
        "proveedor": "NVIDIA NIM",
        "identificador_modelo": MODELO_NVIDIA_NEMOTRON,
        "base_url": NVIDIA_BASE_URL,
        "max_retries": MAX_RETRIES_CLIENTE_NVIDIA,
    }


@lru_cache(maxsize=1)
def obtener_modelo_nvidia() -> ChatOpenAI:
    """Construye el cliente NVIDIA NIM usando su API OpenAI-compatible."""
    load_dotenv()

    api_key = os.getenv("NVIDIA_API_KEY")

    if not api_key:
        raise ValueError(
            "No se encontró NVIDIA_API_KEY. "
            "Verifica que exista en el archivo .env."
        )

    return ChatOpenAI(
        api_key=api_key,
        base_url=NVIDIA_BASE_URL,
        model=MODELO_NVIDIA_NEMOTRON,
        temperature=0,
        max_retries=MAX_RETRIES_CLIENTE_NVIDIA,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    )