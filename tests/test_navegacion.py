"""Navegación por pestañas: el estado sobrevive al cambio y OCI sigue conectado."""

import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from src.app.navegacion import CLAVE_NAVEGACION, CLAVE_PLANTILLA, PESTANAS

pytestmark = pytest.mark.skipif(
    any(importlib.util.find_spec(n) is None for n in ("streamlit", "oci", "pandas", "altair")),
    reason="Prueba de UI requiere dependencias de producción",
)

APP = str(Path(__file__).resolve().parents[1] / "src/app/app.py")


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
    app.run()
    assert not app.exception
    return app


def ir_a(app, pestana):
    app.session_state[CLAVE_NAVEGACION] = pestana
    app.run()
    assert not app.exception


def test_las_siete_pestanas_en_el_orden_pedido():
    assert PESTANAS == ("Inicio", "Plantillas", "Resultado", "Agente en vivo", "Analíticas", "Ayuda", "Datos")


def test_cambiar_de_pestana_conserva_lote_y_aprobaciones():
    app = crear_app(salida())
    original = app.session_state["resultado"]
    next(b for b in app.button if b.key.endswith("int-demo_linkedin")).click().run()
    assert not app.button(key="guardar_aprobados_oci").disabled
    for pestana in PESTANAS:
        ir_a(app, pestana)
        assert app.session_state["resultado"] is original
        assert not app.button(key="guardar_aprobados_oci").disabled


def test_boton_oci_visible_y_conectado_a_curaduria():
    app = crear_app(salida())
    ir_a(app, "Resultado")
    assert app.button(key="guardar_aprobados_oci").disabled
    next(b for b in app.button if b.key.endswith("int-demo_linkedin")).click().run()
    with patch("src.config.oci_client.subir_json") as subir:
        subir.return_value = {"object_name": "objeto.json", "etag": "recibo"}
        app.button(key="guardar_aprobados_oci").click().run()
        assert not app.exception
        subir.assert_called_once()
        assert subir.call_args.args[0]["tipo"] == "linkedin"


def test_tarjeta_del_catalogo_abre_su_plantilla_en_resultado():
    app = crear_app(salida())
    app.button(key="pl_abrir_linkedin").click().run()
    assert not app.exception
    assert app.session_state[CLAVE_NAVEGACION] == "Resultado"
    assert app.session_state[CLAVE_PLANTILLA] == "Publicación para LinkedIn"
    assert app.button(key="pl_abrir_x").disabled


@pytest.mark.parametrize("boton, destino", [
    ("inicio_explorar_plantillas", "Plantillas"),
    ("inicio_hablar_agente", "Agente en vivo"),
    ("inicio_nav_ayuda", "Ayuda"),
    ("inicio_ir_datos", "Datos"),
])
def test_botones_de_inicio_navegan(boton, destino):
    app = crear_app()
    app.button(key=boton).click().run()
    assert not app.exception
    assert app.session_state[CLAVE_NAVEGACION] == destino


def test_sin_lote_resultado_invita_a_cargar_datos():
    app = crear_app()
    assert any("Todavía no hay resultados" in i.value for i in app.info)
    app.button(key="resultado_ir_datos").click().run()
    assert app.session_state[CLAVE_NAVEGACION] == "Datos"
