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