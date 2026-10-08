from unittest.mock import patch

import pytest

from src.agentes.configuracion_ia import (
    MAX_RETRIES_CLIENTE_NVIDIA,
    MODELO_NVIDIA_NEMOTRON,
    NVIDIA_BASE_URL,
    obtener_timeout_nvidia,
)
from src.agentes.errores_ia import ErrorConfiguracionProveedor
from src.agentes.proveedores import nvidia_nim


def test_configuracion_nvidia():
    configuracion = nvidia_nim.obtener_configuracion_nvidia()

    assert configuracion == {
        "proveedor": "NVIDIA NIM",
        "identificador_modelo": MODELO_NVIDIA_NEMOTRON,
        "base_url": NVIDIA_BASE_URL,
        "max_retries": MAX_RETRIES_CLIENTE_NVIDIA,
    }


def test_nvidia_requiere_api_key(monkeypatch):
    nvidia_nim.obtener_modelo_nvidia.cache_clear()

    monkeypatch.delenv(
        "NVIDIA_API_KEY",
        raising=False,
    )

    with patch.object(
        nvidia_nim,
        "load_dotenv",
        return_value=None,
    ):
        with pytest.raises(
            ErrorConfiguracionProveedor,
            match="NVIDIA_API_KEY",
        ):
            nvidia_nim.obtener_modelo_nvidia()

    nvidia_nim.obtener_modelo_nvidia.cache_clear()


def test_construye_cliente_nvidia_sin_realizar_llamada(monkeypatch):
    nvidia_nim.obtener_modelo_nvidia.cache_clear()

    monkeypatch.setenv(
        "NVIDIA_API_KEY",
        "clave-de-prueba",
    )

    monkeypatch.delenv(
        "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS",
        raising=False,
    )

    with patch.object(
        nvidia_nim,
        "load_dotenv",
        return_value=None,
    ), patch.object(
        nvidia_nim,
        "ChatOpenAI",
    ) as cliente:
        nvidia_nim.obtener_modelo_nvidia()

    cliente.assert_called_once_with(
        api_key="clave-de-prueba",
        base_url=NVIDIA_BASE_URL,
        model=MODELO_NVIDIA_NEMOTRON,
        temperature=0,
        timeout=3.0,
        max_retries=0,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    )

    nvidia_nim.obtener_modelo_nvidia.cache_clear()


def test_timeout_nvidia_por_defecto(monkeypatch):
    monkeypatch.delenv(
        "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS",
        raising=False,
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        assert obtener_timeout_nvidia() == 3.0


def test_timeout_nvidia_configurable(monkeypatch):
    monkeypatch.setenv(
        "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS",
        "5.0",
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        assert obtener_timeout_nvidia() == 5.0


def test_timeout_nvidia_invalido_es_error_de_configuracion(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS",
        "invalido",
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        with pytest.raises(
            ErrorConfiguracionProveedor,
            match="COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS",
        ):
            obtener_timeout_nvidia()


def test_timeout_nvidia_debe_ser_mayor_que_cero(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS",
        "0",
    )

    with patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ):
        with pytest.raises(
            ErrorConfiguracionProveedor,
            match="mayor que cero",
        ):
            obtener_timeout_nvidia()