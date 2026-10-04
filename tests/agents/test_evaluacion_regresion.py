import json
from pathlib import Path
from typing import get_args

from scripts.evaluar_casos_ambiguos import (
    CAMPOS_EVALUADOS,
    RUTA_EJECUCION_ANTERIOR,
    RUTA_REFERENCIA,
    UMBRALES_MINIMOS,
    _evaluacion_aprobada,
    calcular_metricas,
    cargar_interacciones,
    evaluar_rutas_referencia,
)
from src.agentes.nodos.nodo_enrutador import determinar_rutas
from src.agentes.modelos import Sentimiento, TemaPrincipal, TipoInteraccion


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
RUTA_CASOS_CANDIDATOS = (
    RAIZ_REPOSITORIO
    / "tests/fixtures/casos_referencia_ia_candidatos.json"
)


def test_casos_candidatos_tienen_esquema_y_rutas_consistentes():
    documento = json.loads(RUTA_CASOS_CANDIDATOS.read_text(encoding="utf-8"))
    interacciones = documento["interacciones"]
    ids = [interaccion["id"] for interaccion in interacciones]

    assert documento["estado_revision"] == "pendiente_revision_humana"
    assert len(interacciones) == documento["cobertura"]["cantidad"] == 10
    assert len(ids) == len(set(ids))
    assert {
        interaccion["tipo_detectado"] for interaccion in interacciones
    } == {
        "testimonio",
        "pregunta_tecnica",
        "pregunta_programa",
        "comentario",
        "feedback",
    }

    datos = json.loads(
        (RAIZ_REPOSITORIO / documento["origen_datos"]).read_text(encoding="utf-8")
    )
    evidencia = json.loads(
        (RAIZ_REPOSITORIO / documento["origen_contexto_rutas"]).read_text(
            encoding="utf-8"
        )
    )
    origen_por_id = {
        interaccion["id"]: interaccion
        for lote in datos["lotes"]
        for interaccion in lote["interacciones"]
    }
    evidencia_por_id = {
        interaccion["id"]: interaccion
        for interaccion in evidencia["interacciones"]
    }
    for interaccion in interacciones:
        assert interaccion["id"] in origen_por_id
        mensaje_origen = origen_por_id[interaccion["id"]]
        contexto_evidencia = evidencia_por_id[interaccion["id"]]
        for campo in ("texto", "autor", "canal", "idioma"):
            assert interaccion[campo] == mensaje_origen[campo]
        for campo in ("score_relevancia", "elegible_contenido", "elegible_faq"):
            assert interaccion[campo] == contexto_evidencia.get(campo, False)
        assert interaccion["tipo_original"] == mensaje_origen["tipo"]
        assert interaccion["sentimiento"] in get_args(Sentimiento)
        assert interaccion["tema_principal"] in get_args(TemaPrincipal)
        assert interaccion["tipo_detectado"] in get_args(TipoInteraccion)
        assert interaccion["justificacion"].strip()
        assert determinar_rutas(interaccion)["rutas"] == interaccion["rutas"]


def test_referencias_miden_las_cuatro_dimensiones_y_rutas():
    referencias = cargar_interacciones(RUTA_REFERENCIA)
    ejecucion_anterior = cargar_interacciones(RUTA_EJECUCION_ANTERIOR)
    evaluacion = calcular_metricas(referencias, ejecucion_anterior)

    assert len(referencias) == 23
    assert set(evaluacion["metricas"]) == set(CAMPOS_EVALUADOS)
    assert all(
        puntaje >= UMBRALES_MINIMOS[campo]
        for campo, puntaje in evaluacion["metricas"].items()
    )
    assert set(evaluacion["metricas_por_clase"]) == set(CAMPOS_EVALUADOS)
    assert all(
        {"precision", "recall", "f1", "soporte"} <= set(metricas)
        for clases in evaluacion["metricas_por_clase"].values()
        for metricas in clases.values()
    )
    assert evaluar_rutas_referencia(referencias) == []


def test_regresion_reporta_campo_y_id_que_cambio():
    referencia = [
        {
            "id": "caso-1",
            "sentimiento": "positivo",
            "tema_principal": "comunidad",
            "tipo_detectado": "comentario",
            "rutas": [],
        }
    ]
    prediccion = [
        {
            **referencia[0],
            "tema_principal": "mentoria",
        }
    ]

    evaluacion = calcular_metricas(referencia, prediccion)

    assert evaluacion["metricas"]["tema_principal"] == 0
    assert not _evaluacion_aprobada(evaluacion)
    assert evaluacion["discrepancias"] == [
        {
            "id": "caso-1",
            "campo": "tema_principal",
            "esperado": "comunidad",
            "obtenido": "mentoria",
        }
    ]


def test_matriz_de_tipo_muestra_feedback_confundido_con_comentario():
    referencia = [
        {
            "id": "caso-feedback",
            "sentimiento": "negativo",
            "tema_principal": "plataforma",
            "tipo_detectado": "feedback",
            "rutas": ["insight_mejora"],
        }
    ]
    prediccion = [
        {
            **referencia[0],
            "tipo_detectado": "comentario",
        }
    ]

    evaluacion = calcular_metricas(referencia, prediccion)

    assert evaluacion["metricas_por_clase"]["tipo_detectado"]["feedback"] == {
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "soporte": 1,
    }
    assert evaluacion["matrices_confusion"]["tipo_detectado"]["feedback"][
        "comentario"
    ] == 1