from pathlib import Path
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

from src.app import fuente_agente, vista_plantillas_diarias


RAIZ = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("valor", ["1", "true", "si"])
def test_marketing_no_habilita_datos_por_variable_ni_estado(monkeypatch, valor):
    monkeypatch.setenv("COMMUNITYLAB_MODO_INTERNO", valor)
    app = AppTest.from_file(str(RAIZ / "src/app/app.py"), default_timeout=30)
    app.session_state["navegacion_principal"] = "Datos"
    app.session_state["resultado"] = {"resultados_por_id": {}}
    app.run()

    assert not app.exception
    assert "Datos" not in app.radio(key="navegacion_principal").options
    assert app.radio(key="navegacion_principal").value == "Inicio"
    assert app.warning
    assert not app.get("file_uploader")
    assert not any(b.key == "procesar_lote" for b in app.button)


def test_marketing_ignora_lote_interno_y_lee_base(monkeypatch):
    lector = Mock(side_effect=fuente_agente.FuenteNoDisponible(fuente_agente.NO_CONFIGURADA))
    monkeypatch.setattr(fuente_agente, "leer_base", lector)
    app = AppTest.from_file(str(RAIZ / "src/app/app.py"), default_timeout=30)
    app.session_state["navegacion_principal"] = "Agente"
    app.session_state["resultado"] = {"resultados_por_id": {"interno": {
        "id": "interno", "texto": "Solo para revision interna",
    }}}
    app.run()

    assert not app.exception
    lector.assert_called_once()
    assert any(fuente_agente.NO_CONFIGURADA in i.value for i in app.info)


def test_marketing_no_expone_curaduria_interna(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_MODO_INTERNO", "1")
    lector = Mock(return_value=None)
    monkeypatch.setattr(vista_plantillas_diarias, "leer_catalogo", lector)
    app = AppTest.from_file(str(RAIZ / "src/app/app.py"), default_timeout=30)
    app.session_state["navegacion_principal"] = "Plantillas"
    app.session_state["resultado"] = {"resultados_por_id": {}}
    app.run()

    assert not app.exception
    lector.assert_called_once()
    assert not app.text_area
    assert not any(b.key == "guardar_aprobados_oci" for b in app.button)


def test_entrada_interna_habilita_datos_sin_variable(monkeypatch):
    monkeypatch.delenv("COMMUNITYLAB_MODO_INTERNO", raising=False)
    app = AppTest.from_file(str(RAIZ / "src/app/app_interna.py"), default_timeout=30)
    app.session_state["navegacion_principal"] = "Datos"
    app.run()

    assert not app.exception
    assert "Datos" in app.radio(key="navegacion_principal").options
    assert len(app.get("file_uploader")) == 1
    assert any(s.value == "Importar interacciones" for s in app.subheader)
