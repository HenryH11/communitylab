"""Adaptador y fallback reales: solo el transporte se sustituye, sin red."""

import json
from unittest.mock import Mock

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableLambda

from src.agentes.modelos import AnalisisMensaje

try:
    from src.agentes.proveedores import nvidia_nim
except ModuleNotFoundError as error:
    if error.name not in {"src.agentes.proveedores", "src.agentes.proveedores.nvidia_nim"}:
        raise
    nvidia_nim = None

pytestmark = pytest.mark.skipif(nvidia_nim is None, reason="El adaptador NIM de DS no está integrado en esta rama")

ANALISIS = {
    "sentimiento": "neutral", "tema_principal": "datos_ia",
    "subtema": "Conexión de nodos", "tipo_detectado": "pregunta_tecnica",
}


def transporte(monkeypatch, contenido):
    llamadas = []

    def responder(mensajes):
        llamadas.append(mensajes)
        if isinstance(contenido, Exception):
            raise contenido
        return AIMessage(content=contenido)

    cliente = Mock()
    cliente.bind.return_value = RunnableLambda(responder)
    monkeypatch.setattr(nvidia_nim, "obtener_modelo_nvidia", lambda: cliente)
    return cliente, llamadas


def test_adaptador_devuelve_cadena_y_valida_salida_del_transporte(monkeypatch):
    cliente, llamadas = transporte(monkeypatch, json.dumps(ANALISIS))
    cadena = nvidia_nim.obtener_modelo_nvidia_estructurado(AnalisisMensaje)
    assert callable(getattr(cadena, "invoke", None)), "El adaptador debe devolver una cadena ejecutable"
    resultado = cadena.invoke([HumanMessage(content="¿Cómo conecto los nodos?")])
    assert isinstance(resultado, AnalisisMensaje)
    assert resultado.model_dump() == ANALISIS
    cliente.bind.assert_called_once_with(response_format={"type": "json_object"})
    assert len(llamadas) == 1
    assert llamadas[0][0].type == "system"
    assert "sentimiento" in llamadas[0][0].content
    assert llamadas[0][-1].content == "¿Cómo conecto los nodos?"


@pytest.mark.parametrize("contenido", ["", "{roto", '{"sentimiento":"otro"}', "[]"])
def test_adaptador_rechaza_salida_inutilizable(monkeypatch, contenido):
    from src.agentes.errores_ia import ErrorSalidaProveedor

    transporte(monkeypatch, contenido)
    cadena = nvidia_nim.obtener_modelo_nvidia_estructurado(AnalisisMensaje)
    assert callable(getattr(cadena, "invoke", None))
    with pytest.raises(ErrorSalidaProveedor):
        cadena.invoke([HumanMessage(content="Mensaje válido")])


@pytest.mark.parametrize("fallo", [None, TimeoutError("timeout simulado"), "{roto"])
def test_cadena_real_usa_nim_y_respalda_solo_si_corresponde(monkeypatch, fallo):
    from src.agentes import cadenas, configuracion_ia, modelo_ia, reintentos

    monkeypatch.setattr(configuracion_ia, "load_dotenv", lambda: None)
    monkeypatch.setenv("COMMUNITYLAB_PROVEEDOR_ANALISIS", "nvidia_nim")
    monkeypatch.setattr(reintentos, "_esperar", lambda segundos: None)
    _, llamadas = transporte(monkeypatch, json.dumps(ANALISIS) if fallo is None else fallo)
    respaldo = Mock(return_value=AnalisisMensaje(**ANALISIS))
    monkeypatch.setattr(modelo_ia, "obtener_modelo_gemini_estructurado", lambda esquema: RunnableLambda(respaldo))
    cadenas._obtener_cadena_analisis.cache_clear()
    try:
        resultado = cadenas.cadena_analisis.invoke({
            "texto": "¿Cómo conecto los nodos de LangGraph?", "origen": "Discord",
            "canal": "#dudas", "idioma": "es", "tipo_original": "pregunta_tecnica",
        })
        assert resultado.model_dump() == ANALISIS
        if fallo is None:
            assert len(llamadas) == 1
            respaldo.assert_not_called()
        else:
            assert len(llamadas) == 3
            respaldo.assert_called_once()
    finally:
        cadenas._obtener_cadena_analisis.cache_clear()
