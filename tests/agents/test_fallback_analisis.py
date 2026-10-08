from unittest.mock import MagicMock, patch

from src.agentes.errores_ia import ErrorSalidaProveedor

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
)
from src.agentes.modelos import AnalisisMensaje
from src.agentes import reintentos
from src.agentes.nodos.nodo_analizador import analizar_mensaje


def _estado():
    return {
        "id": "fallback-001",
        "autor": "Ana",
        "canal": "#dudas",
        "origen": "Discord",
        "idioma": "es",
        "texto": "¿Cómo conecto un nodo en LangGraph?",
        "tipo_original": "pregunta_tecnica",
        "score_relevancia": 80,
        "elegible_contenido": True,
        "elegible_faq": True,
        "rutas": [],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }


def test_analisis_nvidia_falla_y_gemini_respalda(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = TimeoutError(
        "timeout"
    )

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="conexion de nodos",
        tipo_detectado="pregunta_tecnica",
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado["sentimiento"] == "neutral"
    assert resultado["tipo_detectado"] == "pregunta_tecnica"

    assert cadena_nvidia.invoke.call_count == 3
    cadena_gemini.invoke.assert_called_once()

    assert resultado.get("errores", []) == []
    assert resultado.get("fallos", []) == []


def test_analisis_nvidia_salida_invalida_y_gemini_respalda(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = ErrorSalidaProveedor(
        "salida inválida"
    )

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="conexion de nodos",
        tipo_detectado="pregunta_tecnica",
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado["sentimiento"] == "neutral"
    assert resultado["tema_principal"] == "datos_ia"
    assert resultado["tipo_detectado"] == "pregunta_tecnica"

    assert cadena_nvidia.invoke.call_count == 3
    cadena_gemini.invoke.assert_called_once()

    assert resultado.get("errores", []) == []
    assert resultado.get("fallos", []) == []