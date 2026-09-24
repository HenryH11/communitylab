from src.agents.nodes.router_node import determinar_rutas


def test_testimonio_relevante():
    state = {
        "tipo_detectado": "testimonio",
        "sentimiento": "muy_positivo",
        "score_relevancia": 90,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == [
        "caso_exito",
        "linkedin",
    ]


def test_pregunta_tecnica():
    state = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": 75,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == ["faq"]


def test_feedback_no_genera_activo():
    state = {
        "tipo_detectado": "feedback",
        "sentimiento": "negativo",
        "score_relevancia": 80,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == []


def test_comentario_no_genera_activo():
    state = {
        "tipo_detectado": "comentario",
        "sentimiento": "positivo",
        "score_relevancia": 70,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == []


def test_baja_relevancia_no_genera_activo():
    state = {
        "tipo_detectado": "testimonio",
        "sentimiento": "muy_positivo",
        "score_relevancia": 20,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == []

def test_testimonio_neutral_da_solo_caso_exito():
    state = {
        "tipo_detectado": "testimonio",
        "sentimiento": "neutral",
        "score_relevancia": 90,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == ["caso_exito"]


def test_score_ausente_no_bloquea():
    state = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": None,
    }

    resultado = determinar_rutas(state)

    assert resultado["rutas"] == ["faq"]