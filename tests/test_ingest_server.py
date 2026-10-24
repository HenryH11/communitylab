"""Adaptador HTTP real con escritura sustituida; no conecta Oracle ni OCI."""

from contextlib import contextmanager
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from threading import Thread
from unittest.mock import patch

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
