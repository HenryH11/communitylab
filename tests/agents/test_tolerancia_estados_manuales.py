"""Estados construidos sin pasar por la ingesta: qué resiste el grafo y qué no.

Complementa test_tolerancia_fallas.py, que cubre las entradas validadas por
preparar_paquete_ia. Los xfail documentan colapsos reales de src/agentes/
(de Data Science); con strict=True, el test avisa en cuanto se corrijan.
"""

from unittest.mock import MagicMock

import pytest

from src.agentes.nodos import nodo_analizador, nodos_generadores
from src.agentes.nodos.nodo_enrutador import determinar_rutas


def estado(identificador="m-1", **cambios):
    base = {
        "id": identificador, "autor": "Ana", "canal": "#dudas",
        "origen": "Pruebas_Semana3", "idioma": "es",
        "texto": "¿Cómo resuelvo este error en LangGraph? 👩‍💻",
        "tipo_original": "pregunta_tecnica", "score_relevancia": 80,
        "elegible_contenido": True, "elegible_faq": False,
    }
    base.update(cambios)
    return base


@pytest.fixture(autouse=True)
def sin_modelos(monkeypatch):
    """Ninguna prueba de este archivo puede llegar a Gemini."""
    prohibido = MagicMock(side_effect=AssertionError("Llamada a modelo no simulada"))
    individual = MagicMock()
    individual.invoke.side_effect = RuntimeError("proveedor no disponible")
    lote = MagicMock()
    lote.invoke.side_effect = RuntimeError("proveedor no disponible")
    monkeypatch.setattr(nodo_analizador, "cadena_analisis", individual)
    monkeypatch.setattr(nodo_analizador, "cadena_analisis_lote", lote)
    monkeypatch.setattr(nodos_generadores, "_obtener_generadores", prohibido)
    return individual, lote


def test_analisis_individual_sin_texto_queda_como_fallo_trazable():
    sin_texto = estado()
    del sin_texto["texto"]
    resultado = nodo_analizador.analizar_mensaje(sin_texto)
    assert resultado["fallos"][0]["etapa"] == "analizar_mensaje"
    assert resultado["fallos"][0]["id"] == "m-1"
    assert resultado["fallos"][0]["tipo_error"] == "KeyError"


@pytest.mark.parametrize("texto", [None, "", 123, "\ud800"])
def test_analisis_individual_con_texto_anomalo_no_colapsa(texto):
    resultado = nodo_analizador.analizar_mensaje(estado(texto=texto))
    assert resultado["fallos"][0]["id"] == "m-1"
    assert resultado["errores"]


def test_enrutador_tolera_estado_sin_campos():
    assert determinar_rutas({}) == {"rutas": []}


def test_generacion_sin_rutas_no_toca_texto_ni_modelos():
    sin_texto = estado(rutas=[])
    del sin_texto["texto"]
    resultado = nodos_generadores.generar_activos(sin_texto)
    assert resultado["activos_generados"] == {}
    assert resultado["fallos"] == []


@pytest.mark.xfail(strict=True, raises=KeyError, reason=(
    "nodo_analizador.analizar_lote arma los mensajes con estado['texto'] "
    "fuera del try: un estado sin texto aborta todo el lote (DS)"
))
def test_lote_con_un_estado_sin_texto_no_aborta_a_los_demas():
    estados = [estado("m-1"), estado("m-2")]
    del estados[1]["texto"]
    resultados = nodo_analizador.analizar_lote(estados)
    assert len(resultados) == 2
    assert all(r["fallos"] for r in resultados)


@pytest.mark.xfail(strict=True, raises=KeyError, reason=(
    "nodos_generadores._contexto lee estado['texto'] fuera del try: "
    "con rutas y sin texto, generar_activos lanza KeyError (DS)"
))
def test_generacion_con_rutas_y_sin_texto_registra_fallo_por_ruta():
    sin_texto = estado(rutas=["preguntas_frecuentes"])
    del sin_texto["texto"]
    resultado = nodos_generadores.generar_activos(sin_texto)
    assert resultado["activos_generados"] == {}
    assert resultado["fallos"][0]["ruta"] == "preguntas_frecuentes"


@pytest.mark.xfail(strict=True, raises=TypeError, reason=(
    "nodo_enrutador compara score_relevancia < UMBRAL sin validar tipo: "
    "un score de texto sin elegible_contenido lanza TypeError (DS)"
))
def test_enrutador_con_score_no_numerico_no_colapsa():
    resultado = determinar_rutas(estado(
        tipo_detectado="pregunta_tecnica", elegible_contenido=None,
        score_relevancia="80",
    ))
    assert isinstance(resultado["rutas"], list)


@pytest.mark.xfail(strict=True, raises=TypeError, reason=(
    "nodo_enrutador evalúa sentimiento in {...}: un valor no hashable "
    "en un testimonio lanza TypeError (DS)"
))
def test_enrutador_con_sentimiento_no_hashable_no_colapsa():
    resultado = determinar_rutas(estado(
        tipo_detectado="testimonio", sentimiento=["positivo"],
    ))
    assert isinstance(resultado["rutas"], list)
