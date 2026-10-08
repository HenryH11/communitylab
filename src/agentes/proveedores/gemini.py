"""Proveedor Google Gemini para el pipeline de Ciencia de Datos."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

MODELO_GEMINI = "gemini-3.5-flash-lite"

# Bajo a propósito: los reintentos de la aplicación
# (reintentos.py) se suman a estos.
MAX_RETRIES_GEMINI = 2

INTERVALO_REVISION_LIMITADOR = 0.1
TAMANO_MAXIMO_LIMITADOR = 1

# Límite observado en Gemini Free Tier:
# 15 requests por minuto para este modelo.
#
# Trabajamos a ~12 RPM para dejar margen.
SOLICITUDES_POR_SEGUNDO = 0.20


def obtener_configuracion_modelo() -> dict[str, str | int | float]:
    """Devuelve los parámetros no secretos usados en las llamadas a Gemini."""
    return {
        "proveedor": "Google Gemini",
        "identificador_modelo": MODELO_GEMINI,
        "max_retries": MAX_RETRIES_GEMINI,
        "solicitudes_por_segundo": SOLICITUDES_POR_SEGUNDO,
        "intervalo_revision_limitador_segundos": (
            INTERVALO_REVISION_LIMITADOR
        ),
        "tamano_maximo_limitador": TAMANO_MAXIMO_LIMITADOR,
    }


_rate_limiter = InMemoryRateLimiter(
    requests_per_second=SOLICITUDES_POR_SEGUNDO,
    check_every_n_seconds=INTERVALO_REVISION_LIMITADOR,
    max_bucket_size=TAMANO_MAXIMO_LIMITADOR,
)


@lru_cache(maxsize=1)
def obtener_modelo_gemini() -> ChatGoogleGenerativeAI:
    """
    Carga las credenciales y crea un único cliente compartido.

    El rate limiter evita ráfagas de solicitudes que puedan superar
    el límite de Gemini. max_retries permite recuperar llamadas
    transitorias que fallen por rate limit o disponibilidad.
    """
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "No se encontró GEMINI_API_KEY. "
            "Verifica que exista en el archivo .env."
        )

    return ChatGoogleGenerativeAI(
        api_key=api_key,
        model=MODELO_GEMINI,
        rate_limiter=_rate_limiter,
        max_retries=MAX_RETRIES_GEMINI,
    )


def obtener_modelo_gemini_estructurado(
    esquema: type[BaseModel],
):
    """Adapta Gemini al contrato estructurado solicitado."""
    return obtener_modelo_gemini().with_structured_output(
        esquema
    )