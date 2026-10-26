"""Revisión estática de la app de Streamlit frente a archivos anómalos.

No importa Streamlit ni ejecuta la app: analiza src/app/interfaz.py con ast, de
modo que corre en cualquier entorno del equipo. La lectura protegida del
archivo subido la corrigió Soluciones de Software (PR #19).
"""

import ast
from pathlib import Path

import pytest


APP = Path(__file__).resolve().parents[1] / "src" / "app" / "interfaz.py"


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


def test_app_solo_recarga_al_quitar_un_adjunto(arbol):
    """Sin recargas automáticas que disparen ráfagas a la IA."""
    recargas = llamadas(arbol, "st", "rerun")
    assert len(recargas) == 1
    recarga = recargas[0]
    assert not recarga.args
    assert len(recarga.keywords) == 1
    assert recarga.keywords[0].arg == "scope"
    assert isinstance(recarga.keywords[0].value, ast.Constant)
    assert recarga.keywords[0].value.value == "app"
    assert any(
        isinstance(nodo, ast.If)
        and isinstance(nodo.test, ast.Name)
        and nodo.test.id == "quitar"
        and len(nodo.body) == 1
        and isinstance(nodo.body[0], ast.Expr)
        and nodo.body[0].value is recarga
        for nodo in ast.walk(arbol)
    )
    assert llamadas(arbol, "st", "experimental_rerun") == []


def test_procesamiento_con_ia_esta_protegido(arbol):
    for nombre in ("preparar_paquete_ia", "procesar_paquete_entrega"):
        nodos = [
            n for n in ast.walk(arbol)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == nombre
        ]
        assert nodos, f"interfaz.py ya no llama a {nombre}"
        assert all(dentro_de_try(arbol, n) for n in nodos)


def test_errores_se_muestran_en_pantalla(arbol):
    assert llamadas(arbol, "st", "error")


def test_agente_tiene_chat_conectado_al_backend_y_verificacion(arbol):
    assert llamadas(arbol, "st", "chat_message")
    assert any(
        isinstance(nodo, ast.Call) and ast.unparse(nodo.func) == "st.bottom.chat_input"
        for nodo in ast.walk(arbol)
    )
    assert llamadas(arbol, "st", "toggle")

    consultas = [
        nodo
        for nodo in ast.walk(arbol)
        if isinstance(nodo, ast.Call)
        and isinstance(nodo.func, ast.Attribute)
        and nodo.func.attr == "consultar"
    ]
    assert len(consultas) == 1
    assert any(
        argumento.arg == "modo_verificacion"
        for argumento in consultas[0].keywords
    )


# Regresión: SS movió json.load dentro del try (PR #19).
def test_lectura_del_archivo_subido_esta_protegida(arbol):
    cargas = llamadas(arbol, "json", "load") + llamadas(arbol, "json", "loads")
    assert cargas
    assert all(dentro_de_try(arbol, n) for n in cargas)
