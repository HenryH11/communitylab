"""Recorrido de curaduría y guardado con Streamlit y OCI simulado."""

import asyncio
import importlib.util
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from src.app.curaduria_oci import contexto_curaduria, guardar_curaduria


def salida():
    item = {
        "id": "int-demo", "autor": "María", "canal": "discord",
        "sentimiento": "positivo", "tema_principal": "aprendizaje",
        "subtema": "Python", "tipo_detectado": "testimonio",
        "es_spam_detectado": False, "motivo_spam": None,
        "rutas": ["linkedin", "boletin"], "errores": [], "fallos": [],
        "activos_generados": {
            "linkedin": {
                "titulo": "Título original", "contenido": "Contenido original",
                "hashtags": ["#Python", "#Comunidad", "#Aprendizaje"],
            },
            "boletin": {
                "seccion": "Logro", "titular": "Original", "resumen": "Resumen",
            },
        },
    }
    return {
        "resultados": [item], "resultados_por_id": {item["id"]: item},
        "pendientes": [], "ids_pendientes": [],
    }


def test_resultado_nuevo_no_hereda_aprobaciones_aun_con_mismo_contenido():
    sesion = {}
    original = salida()
    contexto = contexto_curaduria(sesion, original)
    contexto["aprobados"][("int-demo", "linkedin")] = {"texto": "Viejo"}
    assert contexto_curaduria(sesion, original) is contexto
    nuevo = contexto_curaduria(sesion, deepcopy(original))
    assert nuevo["lote"] != contexto["lote"]
    assert nuevo["aprobados"] == nuevo["guardados"] == {}


def test_valida_todas_las_ediciones_antes_de_llamar_al_guardado():
    original = salida()
    with patch("src.app.curaduria_oci.guardar_resultado_aprobado") as guardar:
        with pytest.raises(ValueError):
            asyncio.run(guardar_curaduria(
                original,
                {("int-demo", "linkedin"): {"titulo": "Sin campos obligatorios"}},
                periodo="2026-10", bucket="bucket-prueba",
            ))
        guardar.assert_not_called()


con_entorno_ui = pytest.mark.skipif(
    any(importlib.util.find_spec(nombre) is None for nombre in (
        "streamlit", "oci", "pandas", "altair"
    )),
    reason="Prueba de UI requiere dependencias de producción",
)


def crear_app():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src/app/app.py"),
        default_timeout=30,
    )
    app.session_state["resultado"] = salida()
    app.run()
    assert not app.exception
    return app


def editor(app, sufijo):
    return next(campo for campo in app.text_area if campo.key.endswith(sufijo))


def aprobar(app, tipo="linkedin"):
    boton = next(b for b in app.button if b.key.endswith(f"int-demo_{tipo}"))
    boton.click().run()
    assert not app.exception


@con_entorno_ui
def test_ui_sube_texto_editado_sin_modificar_ds_y_solo_una_vez():
    app = crear_app()
    original = deepcopy(app.session_state["resultado"])
    with patch("src.config.oci_client.subir_json") as subir:
        subir.return_value = {"object_name": "objeto.json", "etag": "recibo"}
        assert app.button(key="guardar_aprobados_oci").disabled
        editor(app, "linkedin_contenido").set_value("¡Editado! Ñ 👩‍💻").run()
        aprobar(app)
        app.button(key="guardar_aprobados_oci").click().run()
        assert not app.exception
        subir.assert_called_once()
        contenido = subir.call_args.args[0]
        assert contenido["contenido"]["contenido"] == "¡Editado! Ñ 👩‍💻"
        assert contenido["tipo"] == "linkedin"
        assert app.session_state["resultado"] == original
        app.run()
        assert app.button(key="guardar_aprobados_oci").disabled
        subir.assert_called_once()


@con_entorno_ui
def test_ui_edicion_posterior_y_otro_lote_exigen_aprobar_otra_vez():
    app = crear_app()
    aprobar(app)
    assert not app.button(key="guardar_aprobados_oci").disabled
    editor(app, "linkedin_contenido").set_value("Cambio sin aprobar").run()
    assert app.button(key="guardar_aprobados_oci").disabled
    aprobar(app)
    app.session_state["resultado"] = salida()
    app.run()
    assert app.button(key="guardar_aprobados_oci").disabled
    assert editor(app, "linkedin_contenido").value == "Contenido original"


@con_entorno_ui
def test_ui_reintenta_solo_fallidos_y_no_muestra_error_interno():
    app = crear_app()
    aprobar(app)
    aprobar(app, "boletin")
    with patch("src.config.oci_client.subir_json") as subir:
        subir.side_effect = [
            {"object_name": "linkedin.json", "etag": "ok"},
            RuntimeError("secreto-que-no-debe-aparecer"),
        ]
        app.button(key="guardar_aprobados_oci").click().run()
        assert not app.exception
        assert len(app.error) == 1
        assert "secreto-que-no-debe-aparecer" not in app.error[0].value
        subir.reset_mock(side_effect=True)
        subir.return_value = {"object_name": "boletin.json", "etag": "ok"}
        app.button(key="guardar_aprobados_oci").click().run()
        subir.assert_called_once()
        assert subir.call_args.args[0]["tipo"] == "boletin"


@con_entorno_ui
def test_ui_hashtags_invalidos_no_se_aprueban():
    app = crear_app()
    editor(app, "linkedin_hashtags").set_value("#Uno").run()
    aprobar(app)
    assert app.button(key="guardar_aprobados_oci").disabled
    assert len(app.error) == 1
