import io
from unittest.mock import patch
from urllib.error import URLError

import pytest

from src.app.carga_oracle import conservar_conjunto, solicitar


@pytest.fixture(autouse=True)
def almacenamiento_aislado(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


def test_conserva_lote_para_reintento_sin_ia(tmp_path):
    documento = {"total": 1, "texto": "Texto completo"}
    ruta = conservar_conjunto(documento, tmp_path)
    assert conservar_conjunto(documento, tmp_path) == ruta
    import json

    assert json.loads(ruta.read_text(encoding="utf-8")) == documento
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_cliente_envia_documento_identidad_y_naturaleza(monkeypatch):
    monkeypatch.setenv("INGESTOR_URL", "http://ingestor:8000")
    with patch("src.app.carga_oracle.urlopen", return_value=io.BytesIO(b'{"total": 1}')) as abrir:
        assert solicitar("/sincronizar", {"total": 1}, destino={"identidad": "abc"},
                         sintetico=True) == {"total": 1}
    request = abrir.call_args.args[0]
    assert request.full_url == "http://ingestor:8000/sincronizar"
    assert request.get_header("X-communitylab-destino") == "abc"
    assert request.get_header("X-communitylab-sintetico") == "true"


@pytest.mark.parametrize("url", ["", "http://ingestor/sincronizar", "http://user:secret@ingestor"])
def test_cliente_rechaza_configuracion_invalida(monkeypatch, url):
    monkeypatch.setenv("INGESTOR_URL", url)
    with patch("src.app.carga_oracle.urlopen") as abrir, pytest.raises(ValueError):
        solicitar("/destino")
    abrir.assert_not_called()


def test_cliente_timeout_no_declara_exito(monkeypatch):
    monkeypatch.setenv("INGESTOR_URL", "http://ingestor:8000")
    with patch("src.app.carga_oracle.urlopen", side_effect=URLError("timeout")):
        with pytest.raises(RuntimeError, match="puede haberse confirmado"):
            solicitar("/sincronizar", {})


def test_pantalla_confirma_antes_de_cargar_y_verifica():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string("""
from src.app.carga_oracle import render_carga
render_carga({"version": "1.1", "total": 0, "total_spam_excluido": 0, "registros": []})
""", default_timeout=15)
    destino = {"nombre": "demo", "entorno": "demostracion", "total": 23, "identidad": "abc"}
    with patch("src.app.carga_oracle.solicitar", return_value=destino) as solicitar_mock:
        app.run()
        app.button[0].click().run()
        assert not app.exception
        assert app.button[1].disabled
        app.checkbox[1].check().run()
        assert not app.button[1].disabled
        solicitar_mock.side_effect = [{"insertados": 0}, {"verificado": True}]
        app.button[1].click().run()
        assert not app.exception
        assert app.success
        assert [c.args[0] for c in solicitar_mock.call_args_list][-2:] == [
            "/sincronizar", "/verificar",
        ]


def test_pantalla_bloquea_sinteticos_en_produccion():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string("""
from src.app.carga_oracle import render_carga
render_carga({"total": 0, "registros": []})
""", default_timeout=15)
    destino = {"nombre": "real", "entorno": "produccion", "total": 23, "identidad": "abc"}
    with patch("src.app.carga_oracle.solicitar", return_value=destino) as solicitar_mock:
        app.run()
        app.button[0].click().run()
        assert not app.exception
        assert app.error
        assert len(app.button) == 1
        assert solicitar_mock.call_count == 1
