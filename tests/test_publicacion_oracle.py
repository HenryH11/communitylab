"""Contrato UI -> DA -> ingestor, sin proveedores ni conexiones externas."""

from copy import deepcopy
from io import BytesIO
import json
from threading import Thread
from http.server import ThreadingHTTPServer
from http.client import IncompleteRead
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

import pytest

from src.app.publicacion_oracle import (
    ErrorPublicacion, _url_interna, preparar_publicacion, publicar_conjunto,
)


def salida(*ids, spam=()):
    filas = [{
        "id": i, "autor": "Prueba CE", "canal": "discord", "texto": "Accion y aprendizaje con ñ 🚀",
        "sentimiento": "positivo", "tema_principal": "aprendizaje", "subtema": "Python",
        "tipo_detectado": "comentario", "es_spam_detectado": i in spam,
        "motivo_spam": "Promocion no solicitada" if i in spam else None,
        "rutas": [], "activos_generados": {}, "errores": [], "fallos": [],
    } for i in ids]
    return {"resultados": filas, "resultados_por_id": {f["id"]: f for f in filas},
            "pendientes": [], "ids_pendientes": []}


def mensajes(*ids):
    return {"lotes": [{"interacciones": [
        {"id": i, "texto": "Original", "fecha": "2026-10-25T12:00:00Z"} for i in ids
    ]}]}


def recibo(total=1, spam=0, repetido=False):
    return dict(tabla="conjunto_consultable", sincronizados=total,
                insertados=0 if repetido else total, retirados=0, total=total,
                total_spam_excluido=spam, repetido=repetido)


def test_prepara_contrato_da_sin_mutar_y_con_fechas():
    result, source = salida("b", "a", "spam", spam=("spam",)), mensajes("b", "a", "spam")
    original = deepcopy((result, source))
    doc = preparar_publicacion(result, source)
    assert doc["total"] == 2 and doc["total_spam_excluido"] == 1
    assert [f["id"] for f in doc["registros"]] == ["a", "b"]
    assert doc["registros"][0]["fecha"] == "2026-10-25T12:00:00Z"
    assert doc["registros"][0]["contenido_textual"] == result["resultados"][0]["texto"]
    assert (result, source) == original


@pytest.mark.parametrize("tipo", ["vacio", "pendientes", "errores", "duplicados", "canal_null"])
def test_no_publica_un_resultado_incompleto(tipo):
    result = salida("a")
    if tipo == "vacio": result = salida()
    if tipo == "pendientes":
        result.update(pendientes=[{"id": "pendiente"}], ids_pendientes=["pendiente"])
    if tipo == "errores": result["resultados"][0]["errores"] = ["Fallo"]
    if tipo == "duplicados": result["resultados"].append(deepcopy(result["resultados"][0]))
    if tipo == "canal_null": result["resultados"][0]["canal"] = None
    with pytest.raises(ValueError): preparar_publicacion(result, {})


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/sincronizar", "http://10.100.97.159:8000/sincronizar",
    "https://192.168.1.20/sincronizar", "http://localhost:8503/sincronizar",
    "http://[::1]:8000/sincronizar",
])
def test_destino_privado_explicito(url):
    assert _url_interna(url) == url


@pytest.mark.parametrize("url", [
    "", "https://example.com/sincronizar", "http://8.8.8.8/sincronizar",
    "http://169.254.169.254/sincronizar", "file:///etc/passwd",
    "http://10.0.0.1/sincronizar?token=secreto", "http://u:clave@10.0.0.1/sincronizar",
    "http://10.0.0.1/otro", "http://10.0.0.1/sincronizar#algo",
    "http://0.0.0.0/sincronizar", "http://10.0.0.1:99999/sincronizar",
])
def test_rechaza_url_publica_metadatos_o_credenciales(url):
    with pytest.raises(ErrorPublicacion) as error: _url_interna(url)
    assert "secreto" not in str(error.value) and "clave@" not in str(error.value)


class Respuesta(BytesIO):
    status = 200


def enviar_con_respuesta(payload):
    opener = Mock()
    opener.open.return_value = Respuesta(payload)
    doc = preparar_publicacion(salida("a"), mensajes("a"))
    return opener, doc


def test_envia_una_vez_utf8_y_exige_recibo_completo():
    opener, doc = enviar_con_respuesta(json.dumps(recibo()).encode())
    assert publicar_conjunto(doc, url="http://127.0.0.1:8000/sincronizar", opener=opener) == recibo()
    request = opener.open.call_args.args[0]
    assert request.method == "POST" and json.loads(request.data) == doc
    assert opener.open.call_args.kwargs == {"timeout": 15}
    assert opener.open.call_count == 1


@pytest.mark.parametrize("response", [
    b"no es json", b"{}", b"[]", b"null", b"x" * 65537,
    json.dumps(recibo(total=2)).encode(),
    json.dumps(dict(recibo(), retirados=1)).encode(),
    json.dumps(dict(recibo(), repetido="false")).encode(),
    json.dumps(dict(recibo(), insertados=True)).encode(),
    json.dumps(dict(recibo(), repetido=True, insertados=1)).encode(),
])
def test_no_confirma_respuestas_invalidas(response):
    opener, doc = enviar_con_respuesta(response)
    with pytest.raises(ErrorPublicacion):
        publicar_conjunto(doc, url="http://127.0.0.1:8000/sincronizar", opener=opener)


@pytest.mark.parametrize("error", [TimeoutError(), URLError("dato-privado"),
    IncompleteRead(b"dato-privado", 100),
    HTTPError("http://privado", 400, "dato-privado", {}, BytesIO(b"secreto")),
    HTTPError("http://privado", 500, "dato-privado", {}, BytesIO(b"secreto"))])
def test_error_no_expone_detalles_ni_reintenta(error):
    opener, doc = enviar_con_respuesta(b"{}")
    opener.open.side_effect = error
    with pytest.raises(ErrorPublicacion) as result:
        publicar_conjunto(doc, url="http://127.0.0.1:8000/sincronizar", opener=opener)
    assert opener.open.call_count == 1
    assert "secreto" not in str(result.value) and "dato-privado" not in str(result.value)


def test_rechaza_json_no_finito_sin_enviar():
    opener, doc = enviar_con_respuesta(b"{}")
    doc["registros"][0]["fecha"] = float("nan")
    with pytest.raises(ErrorPublicacion):
        publicar_conjunto(doc, url="http://127.0.0.1:8000/sincronizar", opener=opener)
    opener.open.assert_not_called()


@pytest.fixture
def ingestor_local(monkeypatch):
    # HTTP real solo sobre loopback; escritor real con DB transaccional simulada.
    from test_db_client import Conexion
    from src.services import ingest_server
    con = Conexion()
    monkeypatch.setattr(ingest_server, "obtener_conexion", lambda: con)
    server = ThreadingHTTPServer(("127.0.0.1", 0), ingest_server.IngestHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/sincronizar", con
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_http_real_a_b_repetir_b_y_conflicto(ingestor_local):
    url, con = ingestor_local
    a = preparar_publicacion(salida("a", "spam-a", spam=("spam-a",)), mensajes("a"))
    b = preparar_publicacion(salida("b", "spam-b", spam=("spam-b",)), mensajes("b"))
    assert publicar_conjunto(a, url=url)["total"] == 1
    assert publicar_conjunto(b, url=url)["total"] == 2
    retry = publicar_conjunto(b, url=url)
    assert retry["repetido"] and retry["insertados"] == 0
    assert retry["total_spam_excluido"] == 2 and set(con.filas) == {"a", "b"}
    bad = deepcopy(b)
    bad["registros"][0]["contenido_textual"] = "Otro texto"
    with pytest.raises(ErrorPublicacion): publicar_conjunto(bad, url=url)
    assert set(con.filas) == {"a", "b"} and con.meta["total_spam_excluido"] == 2
