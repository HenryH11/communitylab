"""Adaptador HTTP real con escritura sustituida; no conecta Oracle ni OCI."""

from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from threading import Thread
from unittest.mock import MagicMock, patch

import pytest

from src.services import ingest_server


@contextmanager
def servidor_local():
    servidor = ThreadingHTTPServer(("127.0.0.1", 0), ingest_server.IngestHandler)
    hilo = Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    conexion = HTTPConnection("127.0.0.1", servidor.server_port, timeout=5)
    try:
        yield conexion
    finally:
        conexion.close()
        servidor.shutdown()
        servidor.server_close()
        hilo.join(timeout=5)


def test_salud_no_carga_datos_y_rutas_desconocidas_no_escriben():
    with patch.object(ingest_server, "sincronizar_conjunto") as cargar, servidor_local() as con:
        con.request("GET", "/health")
        respuesta = con.getresponse()
        assert respuesta.status == 200
        assert json.loads(respuesta.read()) == {"status": "ok"}
        con.request("POST", "/otra", body=b"{}")
        respuesta = con.getresponse()
        assert respuesta.status == 404
        respuesta.read()
        cargar.assert_not_called()


@pytest.mark.parametrize("error,codigo", [
    (None, 200), (ValueError("documento inválido"), 400),
    (RuntimeError("detalle interno ficticio"), 500),
])
def test_sincronizacion_http_confirma_documento_y_no_expone_errores_internos(error, codigo):
    doc = {"version": "1.1", "registros": []}
    with (
        patch.object(ingest_server, "sincronizar_conjunto",
                     return_value={"total": 0}, side_effect=error) as cargar,
        servidor_local() as con,
    ):
        con.request("POST", "/sincronizar", body=json.dumps(doc).encode("utf-8"))
        respuesta = con.getresponse()
        cuerpo = respuesta.read().decode("utf-8")
        assert respuesta.status == codigo
        cargar.assert_called_once_with(doc, instantanea_completa=True)
        assert "detalle interno ficticio" not in cuerpo


def test_json_invalido_no_llama_al_escritor():
    with patch.object(ingest_server, "sincronizar_conjunto") as cargar, servidor_local() as con:
        con.request("POST", "/sincronizar", body=b"{")
        respuesta = con.getresponse()
        assert respuesta.status == 400
        respuesta.read()
        cargar.assert_not_called()


def test_destino_comprueba_oracle_y_no_escribe():
    with (
        patch.object(ingest_server, "comprobar_destino", return_value={"identidad": "abc"}) as comprobar,
        patch.object(ingest_server, "sincronizar_conjunto") as cargar,
        servidor_local() as con,
    ):
        con.request("GET", "/destino")
        respuesta = con.getresponse()
        assert respuesta.status == 200
        assert json.loads(respuesta.read()) == {"identidad": "abc"}
        comprobar.assert_called_once()
        cargar.assert_not_called()


@pytest.mark.parametrize("identidad,entorno", [("otro", "demostracion"), ("abc", "produccion")])
def test_destino_cambiado_o_sinteticos_en_produccion_no_escriben(identidad, entorno):
    with (
        patch.object(ingest_server, "comprobar_destino",
                     return_value={"identidad": identidad, "entorno": entorno}),
        patch.object(ingest_server, "sincronizar_conjunto") as cargar,
        servidor_local() as con,
    ):
        con.request("POST", "/sincronizar", body=b"{}", headers={
            "X-CommunityLab-Destino": "abc", "X-CommunityLab-Sintetico": "true",
        })
        respuesta = con.getresponse()
        assert respuesta.status == 400
        respuesta.read()
        cargar.assert_not_called()


def test_verificacion_http_no_escribe():
    with (
        patch.object(ingest_server, "verificar_conjunto", return_value={"verificado": False}) as verificar,
        patch.object(ingest_server, "sincronizar_conjunto") as cargar,
        servidor_local() as con,
    ):
        con.request("POST", "/verificar", body=b"{}")
        respuesta = con.getresponse()
        assert respuesta.status == 200
        assert json.loads(respuesta.read()) == {"verificado": False}
        verificar.assert_called_once_with({})
        cargar.assert_not_called()


def test_comprobar_destino_consulta_tablas_sin_publicar_secretos(monkeypatch):
    monkeypatch.setenv("INGESTOR_DESTINO", "demo-aislada")
    monkeypatch.setenv("INGESTOR_ENTORNO", "demostracion")
    conexion = MagicMock()
    cursor = conexion.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = [("BASE_INTERNA", "ESQUEMA"), (23,), (1,), (2,)]
    with patch.object(ingest_server, "obtener_conexion", return_value=conexion):
        destino = ingest_server.comprobar_destino()
    assert destino["total"] == 23
    assert destino["entorno"] == "demostracion"
    assert len(destino["identidad"]) == 64
    assert "BASE_INTERNA" not in json.dumps(destino)
    assert cursor.execute.call_count == 4
    conexion.commit.assert_not_called()


@pytest.mark.parametrize("fila,verificado", [
    (None, False),
    (("#general", "neutral", "aprendizaje", "comentario", "Otro texto", None, None), False),
    (("#general", "neutral", "aprendizaje", "comentario", "Texto completo", None, "Ana"), True),
])
def test_verificar_contenido_real_no_solo_conteo(fila, verificado):
    registro = dict(zip(ingest_server.CAMPOS_CONJUNTO, [
        "demo-1", "#general", "neutral", "aprendizaje", "comentario", "Texto completo", None, "Ana",
    ]))
    documento = {
        "version": "1.2", "campos": list(ingest_server.CAMPOS_CONJUNTO),
        "total": 1, "total_spam_excluido": 0, "registros": [registro],
    }
    conexion = MagicMock()
    cursor = conexion.__enter__.return_value.cursor.return_value.__enter__.return_value
    cursor.fetchone.return_value = fila
    with patch.object(ingest_server, "obtener_conexion", return_value=conexion):
        resultado = ingest_server.verificar_conjunto(documento)
    assert resultado["verificado"] is verificado
    assert resultado["comprobados"] == 1
    conexion.commit.assert_not_called()
