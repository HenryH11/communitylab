"""Cliente compartido de Gemini con inicialización diferida."""

import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


MODELO_GEMINI = "gemini-3.5-flash-lite"


@lru_cache(maxsize=1)
def obtener_modelo_gemini() -> ChatGoogleGenerativeAI:
    """Carga las credenciales y crea el cliente al primer uso."""
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
    )