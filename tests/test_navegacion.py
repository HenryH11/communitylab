"""Navegación por pestañas: el estado sobrevive al cambio y OCI sigue conectado."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

CLAVE_NAVEGACION = "navegacion_principal"
PESTANAS_INTERNAS = ("Inicio", "Datos", "Agente", "Análisis", "Plantillas", "Ayuda")

pytestmark = pytest.mark.skipif(
    any(importlib.util.find_spec(n) is None for n in ("streamlit", "oci", "pandas", "altair")),
    reason="Prueba de UI requiere dependencias de producción",
)

APP = str(Path(__file__).resolve().parents[1] / "src/app/app_interna.py")


def salida():
    item = {
        "id": "int-demo", "autor": "María", "canal": "discord", "texto": "Aprendí mucho",
        "sentimiento": "positivo", "tema_principal": "aprendizaje", "subtema": "Python",
        "tipo_detectado": "testimonio", "es_spam_detectado": False, "motivo_spam": None,
        "rutas": ["linkedin"], "errores": [], "fallos": [],
        "activos_generados": {
            "linkedin": {"titulo": "Título", "contenido": "Contenido",
                         "hashtags": ["#Python", "#Comunidad", "#Aprendizaje"],
                         "canal_recomendado": "LinkedIn Oficial"},
        },
    }
    return {"resultados": [item], "resultados_por_id": {item["id"]: item},
            "pendientes": [], "ids_pendientes": []}


def crear_app(resultado=None):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(APP, default_timeout=60)
    if resultado is not None:
        app.session_state["resultado"] = resultado
    app.session_state[CLAVE_NAVEGACION] = "Plantillas"
    app.run()
    assert not app.exception
    return app


def ir_a(app, pestana):
    app.session_state[CLAVE_NAVEGACION] = pestana
    app.run()
    assert not app.exception


def test_navegacion_interna_conserva_datos_sin_resultado_separado():
    app = crear_app()
    assert tuple(app.radio(key=CLAVE_NAVEGACION).options) == PESTANAS_INTERNAS


def test_cambiar_de_pestana_conserva_lote_y_aprobaciones():
    app = crear_app(salida())
    original = app.session_state["resultado"]
    next(b for b in app.button if b.key.endswith("int-demo_linkedin")).click().run()
    assert not app.button(key="guardar_aprobados_oci").disabled
    for pestana in ("Inicio", "Datos", "Análisis", "Ayuda", "Plantillas"):
        ir_a(app, pestana)
        assert app.session_state["resultado"] is original
    assert not app.button(key="guardar_aprobados_oci").disabled


def test_boton_oci_visible_y_conectado_a_curaduria():
    app = crear_app(salida())
    assert app.button(key="guardar_aprobados_oci").disabled
    next(b for b in app.button if b.key.endswith("int-demo_linkedin")).click().run()
    with patch("src.config.oci_client.subir_json") as subir:
        subir.return_value = {"object_name": "objeto.json", "etag": "recibo"}
        app.button(key="guardar_aprobados_oci").click().run()
        assert not app.exception
        subir.assert_called_once()
        assert subir.call_args.args[0]["tipo"] == "linkedin"


def test_resultados_se_muestran_dentro_de_plantillas():
    app = crear_app(salida())
    assert not app.exception
    assert app.session_state[CLAVE_NAVEGACION] == "Plantillas"
    assert any(t.label == "Publicación para LinkedIn" for t in app.tabs)
    assert any("Próximamente" in i.value for i in app.info)


@pytest.mark.parametrize("boton, destino", [
    ("inicio_nav_plantillas", "Plantillas"),
    ("inicio_nav_análisis", "Análisis"),
    ("inicio_nav_datos", "Datos"),
])
def test_botones_de_inicio_navegan(boton, destino):
    app = crear_app()
    ir_a(app, "Inicio")
    app.button(key=boton).click().run()
    assert not app.exception
    assert app.session_state[CLAVE_NAVEGACION] == destino


def test_sin_lote_plantillas_explica_que_no_hay_resultados():
    app = crear_app()
    assert any("Todavía no hay un lote procesado" in i.value for i in app.info)
    ir_a(app, "Inicio")
    app.button(key="inicio_nav_datos").click().run()
    assert app.session_state[CLAVE_NAVEGACION] == "Datos"
