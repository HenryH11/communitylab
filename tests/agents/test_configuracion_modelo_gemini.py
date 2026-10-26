from unittest.mock import patch

from src.agentes.configuracion_ia import (
    MODELO_GEMINI_POR_DEFECTO,
    obtener_modelo_gemini_id,
)
from src.agentes.proveedores import gemini


def test_modelo_gemini_configurable_por_entorno(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-simulada")
    monkeypatch.setenv(
        "COMMUNITYLAB_MODELO_GEMINI",
        "gemini-modelo-de-prueba",
    )

    gemini.obtener_modelo_gemini.cache_clear()
    try:
        with (
            patch("src.agentes.configuracion_ia.load_dotenv"),
            patch("src.agentes.proveedores.gemini.load_dotenv"),
            patch(
                "src.agentes.proveedores.gemini.ChatGoogleGenerativeAI"
            ) as cliente,
        ):
            gemini.obtener_modelo_gemini()

            assert (
                cliente.call_args.kwargs["model"]
                == "gemini-modelo-de-prueba"
            )
            assert (
                gemini.obtener_configuracion_modelo()["identificador_modelo"]
                == "gemini-modelo-de-prueba"
            )
    finally:
        gemini.obtener_modelo_gemini.cache_clear()


def test_modelo_gemini_predeterminado(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_MODELO_GEMINI", raising=False)

    with patch("src.agentes.configuracion_ia.load_dotenv"):
        assert obtener_modelo_gemini_id() == MODELO_GEMINI_POR_DEFECTO
