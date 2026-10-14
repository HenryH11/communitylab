"""Flujos de Streamlit, estado de sesión y validación sin acceso a red."""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest
from streamlit.testing.v1 import AppTest

from src.app.local import MAX_BYTES, PLANTILLAS, cargar_entrada, ejemplo, simular_plantilla

APP = Path(__file__).resolve().parents[1] / "src/app/app.py"


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    conectar = socket.socket.connect
    def bloquear(sock, direccion):
        # asyncio en Windows usa socketpair sobre loopback para AppTest.
        if isinstance(direccion, tuple) and direccion[0] in {"127.0.0.1", "::1"}:
            return conectar(sock, direccion)
        raise AssertionError("El frontend local no debe abrir conexiones de red")
    monkeypatch.setattr(socket.socket, "connect", bloquear)


@pytest.fixture
def lote():
    return {"origen_comunidad": "Comunidad de prueba", "periodo_referencia": "Semana_01",
            "interacciones": [{"autor": "Ana", "canal": "#general", "tipo": "comentario", "texto": "Una conversación de prueba"}]}


def pulsar(at, etiqueta):
    next(b for b in at.button if b.label == etiqueta).click().run(timeout=30)
    assert not at.exception
    return at


def abrir(at, pagina):
    at.radio(key="pagina").set_value(pagina).run(timeout=30)
    assert not at.exception
    return at


def test_entrada_oficial_multilote_utf8_y_ids(lote):
    mensajes = cargar_entrada(json.dumps(lote).encode("utf-8-sig"))
    assert mensajes[0]["id"] == "local-0001"
    assert lote["interacciones"][0].get("id") is None
    lote2 = deepcopy(lote)
    lote2["interacciones"][0]["id"] = "local-0001"
    assert [m["id"] for m in cargar_entrada(json.dumps({"lotes": [lote, lote2]}))] == ["local-0002", "local-0001"]
    assert len(cargar_entrada(ejemplo())) == 23


@pytest.mark.parametrize("contenido", [b"{", b"[]", b"{}", b"\xff", b'{"lotes": []}', b'{"lotes": [null]}', b'{"lotes": NaN}'])
def test_entradas_invalidas(contenido):
    with pytest.raises(ValueError):
        cargar_entrada(contenido)


def test_limites_vacios_y_duplicados(lote):
    with pytest.raises(ValueError, match="5 MB"):
        cargar_entrada(b" " * (MAX_BYTES + 1))
    lote["interacciones"][0]["id"] = "repetido"
    lote["interacciones"] *= 2
    with pytest.raises(ValueError, match="duplicados"):
        cargar_entrada(json.dumps(lote))
    lote["interacciones"] = [lote["interacciones"][0]]
    lote["interacciones"][0]["texto"] = "  "
    with pytest.raises(ValueError, match="vacío"):
        cargar_entrada(json.dumps(lote))
    lote["interacciones"] = []
    with pytest.raises(ValueError, match="al menos"):
        cargar_entrada(json.dumps(lote))
    lote["interacciones"] = [{"autor": "a", "canal": "c", "tipo": "comentario", "texto": "t"}] * 1001
    with pytest.raises(ValueError, match="1.000"):
        cargar_entrada(json.dumps(lote))


def test_plantillas_son_simulaciones_con_fuentes(lote):
    mensajes = cargar_entrada(ejemplo())
    for plantilla in PLANTILLAS:
        resultado = simular_plantilla(mensajes, plantilla)
        assert resultado["modo"] == "simulado_local"
        assert not resultado["generado_por_ia"] and not resultado["guardado_en_nube"]
        assert resultado["borradores"]
        assert all(set(b["fuentes"]).issubset({m["id"] for m in mensajes}) for b in resultado["borradores"])
    assert simular_plantilla(cargar_entrada(json.dumps(lote)), "Post para LinkedIn")["borradores"] == []


def test_navegacion_sin_datos_y_agente_inactivo():
    at = AppTest.from_file(APP).run(timeout=30)
    assert not at.exception
    for pagina in ["Plantillas", "Analítica", "Agente en vivo", "Ayuda", "Carga", "Inicio"]:
        abrir(at, pagina)
    pulsar(at, "Cargar mis datos")
    assert at.radio(key="pagina").value == "Carga"
    abrir(at, "Agente en vivo")
    assert next(b for b in at.button if b.label == "Enviar consulta").disabled
    assert at.text_area[0].disabled


def test_ejemplo_filtros_metricas_y_persistencia():
    at = abrir(AppTest.from_file(APP).run(timeout=30), "Carga")
    pulsar(at, "Usar ejemplo del proyecto")
    assert len(at.session_state.datos) == 23
    at.text_input[0].set_value("Camila").run(timeout=30)
    assert len(at.dataframe[0].value) == 1
    at.text_input[0].set_value("sin-coincidencia-123").run(timeout=30)
    assert not at.dataframe
    abrir(at, "Analítica")
    assert [(m.label, m.value) for m in at.metric] == [("Mensajes", "23"), ("Canales", "15"), ("Testimonios declarados", "8"), ("Preguntas declaradas", "9")]
    abrir(at, "Plantillas")
    pulsar(at, "Generar borrador simulado")
    assert len(at.session_state.resultado["borradores"]) == 8
    assert at.warning and "SIMULADO" in at.warning[0].value
    at.multiselect[0].set_value([0]).run(timeout=30)
    abrir(at, "Ayuda")
    abrir(at, "Plantillas")
    assert at.multiselect[0].value == [0]
    assert at.session_state.resultado["plantilla"] == "Post para LinkedIn"


def test_error_conserva_lote_valido_y_reemplazo_retira_resultado(lote):
    at = abrir(AppTest.from_file(APP).run(timeout=30), "Carga")
    pulsar(at, "Usar ejemplo del proyecto")
    abrir(at, "Plantillas")
    pulsar(at, "Generar borrador simulado")
    abrir(at, "Carga")
    # Pegar y pulsar sin esperar una recarga intermedia debe leer el valor nuevo.
    at.text_area[0].set_value("{")
    pulsar(at, "Validar JSON pegado")
    assert at.error and "JSON inválido" in at.error[0].value
    assert "columna 2" in at.error[0].value
    assert len(at.session_state.datos) == 23
    assert at.session_state.resultado
    at.text_area[0].set_value(json.dumps(lote))
    pulsar(at, "Validar JSON pegado")
    assert len(at.session_state.datos) == 1
    assert at.session_state.resultado is None
    abrir(at, "Plantillas")
    pulsar(at, "Generar borrador simulado")
    assert not at.session_state.resultado["borradores"]
    abrir(at, "Carga")
    pulsar(at, "Vaciar sesión")
    assert not at.session_state.datos and at.session_state.resultado is None
