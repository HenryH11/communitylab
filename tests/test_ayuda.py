import importlib.util
from pathlib import Path

import pytest

from src.app.vista_ayuda import SECCIONES, filtrar


def _preguntas(secciones):
    return [pregunta for _, _, preguntas in secciones for pregunta, _ in preguntas]


def test_busqueda_vacia_devuelve_todas_las_secciones():
    assert filtrar(SECCIONES, "   ") == list(SECCIONES)


def test_busqueda_ignora_mayusculas_y_acentos():
    preguntas = _preguntas(filtrar(SECCIONES, "VERIFICACION"))

    assert "¿Qué hace la verificación automática?" in preguntas


def test_busqueda_exige_todos_los_terminos():
    preguntas = _preguntas(filtrar(SECCIONES, "agente cuota"))

    assert preguntas == ["¿Qué hace la verificación automática?"]


def test_ayuda_no_menciona_codigo_ni_archivos_internos():
    texto = " ".join(
        f"{pregunta} {respuesta}"
        for _, _, preguntas in SECCIONES
        for pregunta, respuesta in preguntas
    )

    for termino in ("`", ".env", "docs/", "python", "pipeline"):
        assert termino not in texto


def test_busqueda_sin_coincidencias_devuelve_lista_vacia():
    assert filtrar(SECCIONES, "zzzz") == []


@pytest.mark.parametrize("busqueda", ["tokens", "usuarios", "integración oficial"])
def test_pendientes_son_buscables_y_no_se_presentan_como_disponibles(busqueda):
    secciones = filtrar(SECCIONES, busqueda)
    assert secciones
    assert all(titulo == "Pendientes y próximas integraciones" for titulo, _, _ in secciones)
    assert all(
        respuesta.startswith("Pendiente.")
        for _, _, preguntas in secciones
        for _, respuesta in preguntas
    )


def test_horario_de_plantillas_en_ayuda_es_utc():
    respuestas = " ".join(
        respuesta for _, _, preguntas in SECCIONES for _, respuesta in preguntas
    )
    assert "13:00 UTC" in respuestas
    assert "08:00" not in respuestas


@pytest.mark.skipif(
    any(importlib.util.find_spec(n) is None for n in ("streamlit", "oci", "pandas", "altair")),
    reason="Prueba de UI requiere dependencias de producción",
)
def test_pagina_de_ayuda_se_renderiza_sin_lote():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(
        str(Path(__file__).resolve().parents[1] / "src/app/app.py"), default_timeout=30
    )
    app.session_state["navegacion_principal"] = "Ayuda"
    app.run()

    assert not app.exception
    assert not app.expander
    textos = " ".join(bloque.value for bloque in app.markdown)
    assert all(pregunta in textos for pregunta in _preguntas(SECCIONES))
    assert "docs/" not in textos
    assert [boton.label for boton in app.button if boton.label.startswith("Ir a")] == [
        "Ir a Agente",
        "Ir a Agente",
        "Ir a Análisis",
        "Ir a Plantillas",
    ]
