from unittest.mock import patch

import pytest

from src.agentes.configuracion_ia import (
    MAX_RETRIES_CLIENTE_NVIDIA,
    MODELO_NVIDIA_NEMOTRON,
    NVIDIA_BASE_URL,
)
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
            ValueError,
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
        max_retries=0,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    )

    nvidia_nim.obtener_modelo_nvidia.cache_clear()