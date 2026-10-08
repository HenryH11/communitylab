from unittest.mock import MagicMock, patch


import pytest

from src.agentes.modelo_ia import (obtener_modelo_generacion_estructurado,)

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_proveedor_analisis,
    obtener_proveedor_generacion,
)
from src.agentes.modelo_ia import (
    obtener_modelo_analisis_estructurado,
)
from src.agentes.modelos import AnalisisMensaje


def test_gemini_es_proveedor_por_defecto(
    monkeypatch,
):
    monkeypatch.delenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        raising=False,
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        assert (
            obtener_proveedor_analisis()
            == PROVEEDOR_GEMINI
        )


def test_puede_seleccionar_nvidia(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        assert (
            obtener_proveedor_analisis()
            == PROVEEDOR_NVIDIA_NIM
        )


def test_rechaza_proveedor_desconocido(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        "proveedor_inventado",
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        with pytest.raises(
            ValueError,
            match="no soportado",
        ):
            obtener_proveedor_analisis()


def test_fachada_selecciona_nvidia():
    modelo = MagicMock()

    with patch(
        "src.agentes.modelo_ia.obtener_modelo_nvidia_estructurado",
        return_value=modelo,
    ) as obtener:
        resultado = obtener_modelo_analisis_estructurado(
            AnalisisMensaje,
            proveedor=PROVEEDOR_NVIDIA_NIM,
        )

    assert resultado is modelo
    obtener.assert_called_once_with(
        AnalisisMensaje
    )


def test_fachada_selecciona_gemini():
    modelo = MagicMock()

    with patch(
        "src.agentes.modelo_ia.obtener_modelo_gemini_estructurado",
        return_value=modelo,
    ) as obtener:
        resultado = obtener_modelo_analisis_estructurado(
            AnalisisMensaje,
            proveedor=PROVEEDOR_GEMINI,
        )

    assert resultado is modelo
    obtener.assert_called_once_with(
        AnalisisMensaje
    )

def test_gemini_es_proveedor_generacion_por_defecto(
    monkeypatch,
):
    monkeypatch.delenv(
        "COMMUNITYLAB_PROVEEDOR_GENERACION",
        raising=False,
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        assert (
            obtener_proveedor_generacion()
            == PROVEEDOR_GEMINI
        )


def test_puede_seleccionar_nvidia_para_generacion(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_GENERACION",
        PROVEEDOR_NVIDIA_NIM,
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        assert (
            obtener_proveedor_generacion()
            == PROVEEDOR_NVIDIA_NIM
        )


def test_fachada_generacion_selecciona_nvidia():
    modelo = MagicMock()

    with patch(
        "src.agentes.modelo_ia.obtener_modelo_nvidia_estructurado",
        return_value=modelo,
    ) as obtener:
        resultado = obtener_modelo_generacion_estructurado(
            AnalisisMensaje,
            proveedor=PROVEEDOR_NVIDIA_NIM,
        )

    assert resultado is modelo
    obtener.assert_called_once_with(
        AnalisisMensaje
    )