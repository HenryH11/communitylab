"""Catálogo de la página de Plantillas y su render en Streamlit (Semana 5.1)."""

import importlib.util
from pathlib import Path

import pytest

from src.app.plantillas_catalogo import (
    PLANTILLAS,
    borradores,
    contar,
    distribucion,
    filtrar,
    tipos_sin_plantilla,
)
from src.app.curaduria_oci import MODELOS_ACTIVO

POR_ID = {p["id"]: p for p in PLANTILLAS}


def resultados():
    return {
        "a": {"autor": "Ana", "sentimiento": "positivo", "tema_principal": "aprendizaje", "subtema": "Python",
              "activos_generados": {"linkedin": {"titulo": "T", "contenido": "C", "hashtags": ["#a", "#b", "#c"]},
                                    "boletin": {"seccion": "S", "titular": "T", "resumen": "R"}}},
        "b": {"autor": "Luis", "sentimiento": "positivo", "tema_principal": "empleabilidad",
              "activos_generados": {"preguntas_frecuentes": {"tema": "Q", "respuesta": "R"}}},
        "c": {"autor": "Eva", "sentimiento": "negativo", "tema_principal": "aprendizaje", "activos_generados": {}},
    }


def test_cada_tipo_curable_tiene_una_sola_plantilla():
    tipos = [p["tipo"] for p in PLANTILLAS if p["fuente"] == "activo"]
    assert sorted(tipos) == sorted(MODELOS_ACTIVO)
    assert len({p["id"] for p in PLANTILLAS}) == len(PLANTILLAS)


def test_instagram_y_x_quedan_como_proximamente():
    assert POR_ID["instagram"]["fuente"] == POR_ID["x"]["fuente"] == "proxima"
    assert contar(POR_ID["instagram"], resultados()) == 0
    assert borradores(POR_ID["x"], resultados()) == []


def test_contadores_reales_por_plantilla():
    datos = resultados()
    assert contar(POR_ID["linkedin"], datos) == 1
    assert contar(POR_ID["preguntas_frecuentes"], datos) == 1
    assert contar(POR_ID["caso_exito"], datos) == 0
    assert contar(POR_ID["sentimiento"], datos) == 3
    assert [i for i, _, _ in borradores(POR_ID["boletin"], datos)] == ["a"]


def test_distribucion_ordena_de_mayor_a_menor():
    assert distribucion(POR_ID["sentimiento"], resultados()) == [("positivo", 2), ("negativo", 1)]
    assert distribucion(POR_ID["temas"], resultados())[0] == ("aprendizaje", 2)


def lote_con_spam():
    """Caso de Jhonattan: 2 legítimos positivos y 3 spam negativos."""
    datos = {f"ok{i}": {"sentimiento": "positivo", "tema_principal": "aprendizaje", "es_spam_detectado": False,
                        "activos_generados": {}} for i in range(2)}
    datos.update({f"spam{i}": {"sentimiento": "negativo", "tema_principal": "otros", "es_spam_detectado": True,
                               "motivo_spam": "publicidad", "activos_generados": {}} for i in range(3)})
    return datos


def test_sentimiento_excluye_spam_como_ds():
    from src.agentes.resumen_entrega import construir_resumen_comunidad

    datos = lote_con_spam()
    assert distribucion(POR_ID["sentimiento"], datos) == [("positivo", 2)]
    assert contar(POR_ID["sentimiento"], datos) == 2
    resumen = construir_resumen_comunidad(list(datos.values()), [], [], 0)
    assert dict(distribucion(POR_ID["sentimiento"], datos)) == resumen["distribucion_sentimientos"]


def test_temas_cuentan_todos_los_mensajes_como_ds():
    from src.agentes.resumen_entrega import construir_resumen_comunidad

    datos = lote_con_spam()
    resumen = construir_resumen_comunidad(list(datos.values()), [], [], 0)
    assert dict(distribucion(POR_ID["temas"], datos)) == resumen["distribucion_temas"] == {"otros": 3, "aprendizaje": 2}


def test_filtros_por_categoria_y_busqueda():
    assert {p["id"] for p in filtrar(categoria="Preguntas frecuentes")} == {"preguntas_frecuentes"}
    assert [p["id"] for p in filtrar("  LINKEDIN ")] == ["linkedin"]
    assert filtrar("no-existe") == []
    assert len(filtrar()) == len(PLANTILLAS)


def test_tipos_desconocidos_no_se_pierden():
    datos = resultados()
    datos["c"]["activos_generados"]["podcast"] = {"guion": "G"}
    assert tipos_sin_plantilla(datos) == ["podcast"]


con_entorno_ui = pytest.mark.skipif(
    any(importlib.util.find_spec(n) is None for n in ("streamlit", "oci", "pandas", "altair")),
    reason="Prueba de UI requiere dependencias de producción",
)
APP = str(Path(__file__).resolve().parents[1] / "src/app/app_interna.py")


@con_entorno_ui
def test_ui_sin_lote_muestra_catalogo_sin_editores(monkeypatch):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["navegacion_principal"] = "Plantillas"
    app.run()
    assert not app.exception
    assert not app.text_area
    assert any("Todavía no hay un lote procesado" in i.value for i in app.info)


@con_entorno_ui
def test_ui_con_lote_pinta_cada_activo_una_vez_y_proximamente(monkeypatch):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["resultado"] = {"resultados_por_id": resultados()}
    app.session_state["navegacion_principal"] = "Plantillas"
    app.run()
    assert not app.exception
    aprobar = [b.key for b in app.button if b.key and b.key.startswith("btn_")]
    # btn_{lote}_{id}_{tipo}: el lote es hex y los ids de prueba no llevan "_".
    assert sorted(k.split("_", 3)[2] for k in aprobar) == ["a", "a", "b"]
    assert any("Próximamente" in i.value for i in app.info)
    app.text_input(key="plantillas_busqueda").set_value("linkedin").run()
    assert not app.exception


@con_entorno_ui
def test_ui_detalle_incluye_mensajes_sin_activos_y_spam():
    from streamlit.testing.v1 import AppTest

    datos = resultados()
    datos.update(lote_con_spam())
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["resultado"] = {"resultados_por_id": datos}
    app.session_state["navegacion_principal"] = "Análisis"
    app.run()
    assert not app.exception
    detalle = [e for e in app.expander if e.label.startswith(("📝", "💬", "🚫"))]
    assert len(detalle) == len(datos)
    assert sum(e.label.startswith("🚫") for e in detalle) == 3
    assert any("no generó activos" in c.value for c in app.caption)
    assert any("Se excluyen 3 mensaje(s)" in c.value for c in app.caption)
