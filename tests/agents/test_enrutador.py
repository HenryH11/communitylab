from src.agentes.nodos.nodo_enrutador import determinar_rutas


def test_testimonio_relevante():
    estado = {
        "tipo_detectado": "testimonio",
        "sentimiento": "muy_positivo",
        "score_relevancia": 90,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == [
        "caso_exito",
        "boletin",
        "linkedin",
    ]


def test_pregunta_tecnica():
    estado = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": 75,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]


def test_feedback_relevante_genera_insight_mejora():
    estado = {
        "tipo_detectado": "feedback",
        "sentimiento": "negativo",
        "score_relevancia": 80,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["insight_mejora"]


def test_feedback_baja_relevancia_no_genera_insight():
    estado = {
        "tipo_detectado": "feedback",
        "sentimiento": "negativo",
        "score_relevancia": 20,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == []

    
def test_comentario_no_genera_activo():
    estado = {
        "tipo_detectado": "comentario",
        "sentimiento": "positivo",
        "score_relevancia": 70,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == []


def test_baja_relevancia_no_genera_activo():
    estado = {
        "tipo_detectado": "testimonio",
        "sentimiento": "muy_positivo",
        "score_relevancia": 20,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == []


def test_testimonio_neutral_da_caso_exito_y_boletin():
    estado = {
        "tipo_detectado": "testimonio",
        "sentimiento": "neutral",
        "score_relevancia": 90,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == [
        "caso_exito",
        "boletin",
    ]


def test_puntaje_ausente_no_bloquea():
    estado = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": None,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]


def test_pregunta_programa_elegible_faq_genera_faq():
    estado = {
        "tipo_detectado": "pregunta_programa",
        "sentimiento": "neutral",
        "score_relevancia": 62,
        "elegible_contenido": True,
        "elegible_faq": True,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]


def test_pregunta_programa_no_elegible_faq_no_genera_activo():
    estado = {
        "tipo_detectado": "pregunta_programa",
        "sentimiento": "neutral",
        "score_relevancia": 62,
        "elegible_contenido": True,
        "elegible_faq": False,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == []


def test_pregunta_programa_sin_elegible_faq_no_genera_activo():
    estado = {
        "tipo_detectado": "pregunta_programa",
        "sentimiento": "neutral",
        "score_relevancia": 62,
        "elegible_contenido": True,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == []