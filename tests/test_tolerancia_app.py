"""Revisión estática de la app de Streamlit frente a archivos anómalos.

No importa Streamlit ni ejecuta la app: analiza src/app/app.py con ast, de
modo que corre en cualquier entorno del equipo. Los xfail documentan riesgos
reales para Soluciones de Software.
"""

import ast
from pathlib import Path

import pytest


APP = Path(__file__).resolve().parents[1] / "src" / "app" / "app.py"


@pytest.fixture(scope="module")
def arbol():
    return ast.parse(APP.read_text(encoding="utf-8"))


def llamadas(arbol, objeto, atributo):
    return [
        nodo for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == atributo
        and isinstance(nodo.func.value, ast.Name)
        and nodo.func.value.id == objeto
    ]


def dentro_de_try(arbol, objetivo):
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Try) and nodo.handlers:
            for sentencia in nodo.body:
                if any(hijo is objetivo for hijo in ast.walk(sentencia)):
                    return True
    return False


def test_app_no_usa_st_rerun(arbol):
    """Regla del PM (Semana 3): sin recargas que disparen ráfagas a la IA."""
    assert llamadas(arbol, "st", "rerun") == []
    assert llamadas(arbol, "st", "experimental_rerun") == []


def test_procesamiento_con_ia_esta_protegido(arbol):
    for nombre in ("preparar_paquete_ia", "procesar_paquete_entrega"):
        nodos = [
            n for n in ast.walk(arbol)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == nombre
        ]
        assert nodos, f"app.py ya no llama a {nombre}"
        assert all(dentro_de_try(arbol, n) for n in nodos)


def test_errores_se_muestran_en_pantalla(arbol):
    assert llamadas(arbol, "st", "error")


@pytest.mark.xfail(strict=True, reason=(
    "app.py ejecuta json.load(archivo_subido) fuera del try: un JSON truncado, "
    "vacío o no UTF-8 muestra la traza en vez de st.error (SS)"
))
def test_lectura_del_archivo_subido_esta_protegida(arbol):
    cargas = llamadas(arbol, "json", "load") + llamadas(arbol, "json", "loads")
    assert cargas
    assert all(dentro_de_try(arbol, n) for n in cargas)
