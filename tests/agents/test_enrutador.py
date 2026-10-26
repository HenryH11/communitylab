from typing import cast

from src.agentes.estado_agente import EstadoAgente
from src.agentes.nodos.nodo_enrutador import ResultadoRutas, determinar_rutas as _determinar_rutas


def determinar_rutas(estado: dict) -> ResultadoRutas:
    # El enrutador solo lee clasificación y elegibilidad; estos casos omiten id/texto.
    return _determinar_rutas(cast(EstadoAgente, estado))


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


def test_pregunta_programa_faq_es_independiente_de_elegible_contenido():
    estado = {
        "tipo_detectado": "pregunta_programa",
        "sentimiento": "neutral",
        "score_relevancia": 20,
        "elegible_contenido": False,
        "elegible_faq": True,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]


def test_elegible_contenido_prevalece_sobre_puntaje_bajo():
    estado = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": 20,
        "elegible_contenido": True,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]


def test_puntaje_en_umbral_no_bloquea_estado_antiguo():
    estado = {
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": 40,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == ["preguntas_frecuentes"]


def test_tipo_no_reconocido_no_genera_rutas():
    estado = {
        "tipo_detectado": "spam",
        "sentimiento": "neutral",
        "score_relevancia": 80,
    }

    resultado = determinar_rutas(estado)

    assert resultado["rutas"] == []


def test_spam_bloquea_todas_las_rutas():
    escenarios = [
        {
            "tipo_detectado": "testimonio",
            "sentimiento": "muy_positivo",
            "score_relevancia": 95,
            "elegible_contenido": True,
            "elegible_faq": False,
        },
        {
            "tipo_detectado": "pregunta_tecnica",
            "sentimiento": "neutral",
            "score_relevancia": 85,
            "elegible_contenido": True,
            "elegible_faq": False,
        },
        {
            "tipo_detectado": "pregunta_programa",
            "sentimiento": "neutral",
            "score_relevancia": 80,
            "elegible_contenido": True,
            "elegible_faq": True,
        },
    ]

    for escenario in escenarios:
        estado = {
            **escenario,
            "es_spam_detectado": True,
            "motivo_spam": "Promoción no solicitada",
        }

        resultado = determinar_rutas(estado)

        assert resultado["rutas"] == []
        assert estado["score_relevancia"] == escenario["score_relevancia"]
        assert estado["elegible_contenido"] == escenario["elegible_contenido"]
        assert estado["elegible_faq"] == escenario["elegible_faq"]


def test_spam_no_genera_activos_en_langgraph():
    from src.agentes.grafo import (
        comprobar_rutas,
        grafo_desde_analisis,
    )

    estado: EstadoAgente = {
        "id": "spam-grafo-001",
        "texto": "Gana dinero rápido. Escríbeme por privado.",
        "tipo_original": "comentario",
        "tipo_detectado": "testimonio",
        "sentimiento": "muy_positivo",
        "es_spam_detectado": True,
        "motivo_spam": "Captación mediante oferta dudosa",
        "score_relevancia": 95,
        "elegible_contenido": True,
        "elegible_faq": True,
        "rutas": [],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }

    resultado = grafo_desde_analisis.invoke(estado)

    assert resultado["rutas"] == []
    assert resultado["activos_generados"] == {}
    assert comprobar_rutas(cast(EstadoAgente, resultado)) == "finalizar"

    # Las decisiones originales de Data permanecen intactas.
    assert resultado["score_relevancia"] == 95
    assert resultado["elegible_contenido"] is True
    assert resultado["elegible_faq"] is True
