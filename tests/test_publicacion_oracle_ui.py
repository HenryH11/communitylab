"""UI real con procesamiento y transporte sustituidos; sin IA/OCI."""

from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from test_publicacion_oracle import ingestor_local, mensajes, recibo, salida
from src.app.publicacion_oracle import ErrorPublicacion


ROOT = Path(__file__).resolve().parents[1]


def app_interna():
    app = AppTest.from_file(str(ROOT / "src/app/app_interna.py"), default_timeout=30)
    app.session_state["navegacion_principal"] = "Datos"
    return app


def procesar(app, resultado):
    original = mensajes("a")
    with patch("streamlit.file_uploader", side_effect=lambda *a, **k: BytesIO(json.dumps(original).encode())), \
         patch("src.app.interfaz.preparar_paquete_ia", return_value={}), \
         patch("src.app.interfaz.procesar_paquete_entrega", return_value=resultado):
        app.run()
        app.button(key="procesar_lote").click().run()
    assert not app.exception


def confirmar(app):
    next(c for c in app.checkbox if c.key.startswith("confirmar_publicacion_oracle_")).check().run()


def test_solo_publica_con_confirmacion_y_no_repite_en_rerun(monkeypatch):
    monkeypatch.setenv("INGESTOR_URL", "http://127.0.0.1:8000/sincronizar")
    app = app_interna()
    with patch("src.app.publicacion_oracle.publicar_conjunto", return_value=recibo()) as post:
        procesar(app, salida("a"))
        assert post.call_count == 0 and app.button(key="publicar_lote_oracle").disabled
        confirmar(app)
        app.button(key="publicar_lote_oracle").click().run()
        assert not app.exception and post.call_count == 1
        assert post.call_args.args[0]["registros"][0]["fecha"] == "2026-10-25T12:00:00Z"
        app.run()
        assert app.button(key="publicar_lote_oracle").disabled and post.call_count == 1
        assert any("Publicación confirmada" in s.value for s in app.success)


def test_timeout_permite_reintentar_mismo_lote_sin_ia(monkeypatch):
    monkeypatch.setenv("INGESTOR_URL", "http://127.0.0.1:8000/sincronizar")
    app = app_interna()
    procesar(app, salida("a"))
    confirmar(app)
    with patch("src.app.publicacion_oracle.publicar_conjunto", side_effect=[ErrorPublicacion("Sin confirmacion"), recibo(repetido=True)]) as post, \
         patch("src.app.interfaz.procesar_paquete_entrega", side_effect=AssertionError("No reprocesar IA")):
        app.button(key="publicar_lote_oracle").click().run()
        assert app.error and not app.exception
        enviado = deepcopy(post.call_args.args[0])
        app.button(key="publicar_lote_oracle").click().run()
        assert not app.exception and post.call_count == 2
        assert post.call_args.args[0] == enviado
        assert any("ya estaba publicado" in s.value for s in app.success)


def test_no_habilita_si_falta_destino_privado(monkeypatch):
    monkeypatch.delenv("INGESTOR_URL", raising=False)
    app = app_interna()
    procesar(app, salida("a"))
    confirmar(app)
    assert app.button(key="publicar_lote_oracle").disabled


def test_nuevo_procesamiento_requiere_nueva_confirmacion(monkeypatch):
    monkeypatch.setenv("INGESTOR_URL", "http://127.0.0.1:8000/sincronizar")
    app = app_interna()
    procesar(app, salida("a"))
    confirmar(app)
    assert not app.button(key="publicar_lote_oracle").disabled
    procesar(app, salida("b"))
    assert app.button(key="publicar_lote_oracle").disabled


def test_marketing_no_muestra_publicacion_aunque_haya_url_y_resultado(monkeypatch):
    monkeypatch.setenv("INGESTOR_URL", "http://127.0.0.1:8000/sincronizar")
    app = AppTest.from_file(str(ROOT / "src/app/app.py"), default_timeout=30)
    result = salida("a")
    app.session_state["resultado"] = result
    app.session_state["_origen_publicacion_oracle"] = {"resultado": result, "mensajes": mensajes("a")}
    app.session_state["navegacion_principal"] = "Datos"
    with patch("src.app.publicacion_oracle.publicar_conjunto", side_effect=AssertionError("Marketing no publica")):
        app.run()
    assert not app.exception
    assert all(b.key != "publicar_lote_oracle" for b in app.button)
    assert "Datos" not in app.radio[0].options


def test_recorrido_pantalla_a_http_ingestor_con_db_simulada(monkeypatch, ingestor_local):
    url, con = ingestor_local
    monkeypatch.setenv("INGESTOR_URL", url)
    app = app_interna()
    procesar(app, salida("a"))
    confirmar(app)
    app.button(key="publicar_lote_oracle").click().run()
    assert not app.exception
    assert con.filas["a"]["fecha"] == "2026-10-25T12:00:00Z"
    assert con.meta["total"] == 1 and len(con.cargas) == 1
    assert any("Publicación confirmada" in s.value for s in app.success)
    app.run()
    assert con.commits == 1 and len(con.cargas) == 1
