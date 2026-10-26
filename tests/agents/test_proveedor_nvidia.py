from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

import json

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from src.agentes.modelos import AnalisisMensaje

from src.agentes.configuracion_ia import (
    MAX_RETRIES_CLIENTE_NVIDIA,
    MODELO_NVIDIA_POR_DEFECTO,
    NVIDIA_BASE_URL,
    obtener_timeout_nvidia,
)
from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorSalidaProveedor,
)

from src.agentes.proveedores import nvidia_nim


def test_configuracion_nvidia(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_MODELO_NVIDIA", raising=False)

    with patch("src.agentes.configuracion_ia.load_dotenv"):
        configuracion = nvidia_nim.obtener_configuracion_nvidia()

    assert configuracion == {
        "proveedor": "NVIDIA NIM",
        "identificador_modelo": MODELO_NVIDIA_POR_DEFECTO,
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
    monkeypatch.delenv(
        "COMMUNITYLAB_MODELO_NVIDIA",
        raising=False,
    )

    with patch.object(
        nvidia_nim,
        "load_dotenv",
        return_value=None,
    ), patch(
        "src.agentes.configuracion_ia.load_dotenv",
        return_value=None,
    ), patch.object(
        nvidia_nim,
        "ChatOpenAI",
    ) as cliente:
        nvidia_nim.obtener_modelo_nvidia()

    cliente.assert_called_once_with(
        api_key=SecretStr("clave-de-prueba"),
        base_url=NVIDIA_BASE_URL,
        model=MODELO_NVIDIA_POR_DEFECTO,
        temperature=0,
        timeout=15.0,
        max_retries=0,
        extra_body={
            "chat_template_kwargs": {
                "enable_thinking": False,
            }
        },
    )

    nvidia_nim.obtener_modelo_nvidia.cache_clear()


def test_modelo_nvidia_configurable_por_entorno(monkeypatch):
    nvidia_nim.obtener_modelo_nvidia.cache_clear()

    monkeypatch.setenv(
        "NVIDIA_API_KEY",
        "clave-de-prueba",
    )
    monkeypatch.setenv(
        "COMMUNITYLAB_MODELO_NVIDIA",
        "nvidia/nemotron-3-ultra-550b-a55b",
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
        api_key=SecretStr("clave-de-prueba"),
        base_url=NVIDIA_BASE_URL,
        model="nvidia/nemotron-3-ultra-550b-a55b",
        temperature=0,
        timeout=15.0,
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
        assert obtener_timeout_nvidia() == 15.0


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


def test_adaptador_nvidia_devuelve_cadena_y_valida_salida(
    monkeypatch,
):
    respuesta = {
        "sentimiento": "neutral",
        "tema_principal": "datos_ia",
        "subtema": "conexion de nodos",
        "tipo_detectado": "pregunta_tecnica",
        "es_spam_detectado": False,
        "motivo_spam": None,
    }

    cliente = MagicMock()
    cliente.bind.return_value = RunnableLambda(
        lambda _mensajes: AIMessage(
            content=json.dumps(respuesta)
        )
    )

    monkeypatch.setattr(
        nvidia_nim,
        "obtener_modelo_nvidia",
        lambda: cliente,
    )

    cadena = nvidia_nim.obtener_modelo_nvidia_estructurado(
        AnalisisMensaje
    )

    assert callable(
        getattr(cadena, "invoke", None)
    )

    resultado = cadena.invoke(
        [
            HumanMessage(
                content="¿Cómo conecto nodos en LangGraph?"
            )
        ]
    )

    assert isinstance(
        resultado,
        AnalisisMensaje,
    )
    assert resultado.model_dump() == respuesta

    cliente.bind.assert_called_once_with(
        response_format={
            "type": "json_object",
        }
    )


@pytest.mark.parametrize(
    "contenido",
    [
        "",
        "{json roto",
        '{"sentimiento": "otro"}',
        "[]",
    ],
)
def test_adaptador_nvidia_rechaza_salida_invalida(
    monkeypatch,
    contenido,
):
    cliente = MagicMock()
    cliente.bind.return_value = RunnableLambda(
        lambda _mensajes: AIMessage(
            content=contenido
        )
    )

    monkeypatch.setattr(
        nvidia_nim,
        "obtener_modelo_nvidia",
        lambda: cliente,
    )

    cadena = nvidia_nim.obtener_modelo_nvidia_estructurado(
        AnalisisMensaje
    )

    with pytest.raises(ErrorSalidaProveedor):
        cadena.invoke(
            [
                HumanMessage(
                    content="Mensaje válido"
                )
            ]
        )

@pytest.mark.parametrize(
    "modelo, esquema, limite_esperado",
    [
        ("nvidia/nemotron-3.5-super-vl-120b-a12b", "faq", 512),
        ("nvidia/nemotron-3.5-super-vl-120b-a12b", "analisis", None),
        ("openai/gpt-oss-20b", "faq", None),
        (None, "faq", 512),
    ],
)
def test_limite_tokens_selectivo_nemotron35(
    monkeypatch, modelo, esquema, limite_esperado
):
    from unittest.mock import MagicMock
    from src.agentes.modelos import (
        AnalisisMensaje,
        SugerenciaPreguntasFrecuentes,
    )

    cliente = MagicMock()
    cliente.model_name = modelo or (
        "nvidia/nemotron-3.5-super-vl-120b-a12b"
    )

    monkeypatch.setattr(
        nvidia_nim,
        "obtener_modelo_nvidia",
        lambda modelo=None: cliente,
    )

    esquema_pydantic = (
        SugerenciaPreguntasFrecuentes
        if esquema == "faq"
        else AnalisisMensaje
    )

    nvidia_nim.obtener_modelo_nvidia_estructurado(
        esquema_pydantic,
        modelo=modelo,
    )

    cliente.bind.assert_called_once()
    argumentos = cliente.bind.call_args.kwargs

    assert argumentos["response_format"] == {
        "type": "json_object"
    }
    assert argumentos.get("max_tokens") == limite_esperado
