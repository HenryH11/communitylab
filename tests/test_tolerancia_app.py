"""Revisión estática de la app de Streamlit frente a archivos anómalos.

No importa Streamlit ni ejecuta la app: analiza src/app/app.py con ast, de
modo que corre en cualquier entorno del equipo. La lectura protegida del
archivo subido la corrigió Soluciones de Software (PR #19).
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


def test_frontend_local_no_importa_ni_llama_proveedores(arbol):
    """Esta rama es offline: conectar IA requiere una integración explícita."""
    for archivo in (APP, APP.with_name("local.py")):
        codigo = ast.parse(archivo.read_text(encoding="utf-8-sig"))
        for nodo in ast.walk(codigo):
            if isinstance(nodo, ast.ImportFrom):
                assert not (nodo.module or "").startswith(("src.agentes", "src.config", "dotenv"))
            if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name):
                assert nodo.func.id not in {"preparar_paquete_ia", "procesar_paquete_entrega", "guardar_resultado_aprobado"}


def test_errores_se_muestran_en_pantalla(arbol):
    assert llamadas(arbol, "st", "error")


# Regresión: SS movió json.load dentro del try (PR #19).
def test_lectura_del_archivo_subido_esta_protegida(arbol):
    arbol = ast.parse(APP.with_name("local.py").read_text(encoding="utf-8"))
    cargas = llamadas(arbol, "json", "load") + llamadas(arbol, "json", "loads")
    assert cargas
    assert all(dentro_de_try(arbol, n) for n in cargas)
