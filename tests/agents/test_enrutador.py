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


def test_feedback_no_genera_activo():
    estado = {
        "tipo_detectado": "feedback",
        "sentimiento": "negativo",
        "score_relevancia": 80,
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

def test_testimonio_neutral_da_solo_caso_exito():
    estado = {
        "tipo_detectado": "testimonio",
        "sentimiento": "neutral",
        "score_relevancia": 90,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["caso_exito"]


def test_puntaje_ausente_no_bloquea():
    estado = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": None,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]