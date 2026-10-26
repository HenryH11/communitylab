from src.agentes.resumen_entrega import construir_resumen_comunidad


def test_resumen_excluye_spam_pero_conserva_neutrales():
    resultados = [
        {
            "id": "spam-001",
            "sentimiento": "neutral",
            "es_spam_detectado": True,
            "motivo_spam": "Captación mediante oferta dudosa",
        },
        {
            "id": "normal-001",
            "sentimiento": "neutral",
            "es_spam_detectado": False,
            "motivo_spam": None,
        },
        {
            "id": "normal-002",
            "sentimiento": "positivo",
            "es_spam_detectado": False,
            "motivo_spam": None,
        },
        {
            "id": "normal-003",
            "sentimiento": "positivo",
            "es_spam_detectado": False,
            "motivo_spam": None,
        },
    ]

    resumen = construir_resumen_comunidad(
        resultados=resultados,
        activos=[],
        fallos=[],
        total_pendientes=0,
    )

    assert resumen["total_interacciones_procesadas"] == 4
    assert resumen["total_spam_detectado"] == 1
    assert resumen["distribucion_sentimientos"] == {
        "positivo": 2,
        "neutral": 1,
    }
    assert resumen["sentimiento_predominante"] == "positivo"


def test_resumen_cuando_todos_son_spam():
    resultados = [
        {
            "id": "spam-001",
            "sentimiento": "neutral",
            "es_spam_detectado": True,
        },
        {
            "id": "spam-002",
            "sentimiento": "positivo",
            "es_spam_detectado": True,
        },
    ]

    resumen = construir_resumen_comunidad(
        resultados=resultados,
        activos=[],
        fallos=[],
        total_pendientes=0,
    )

    assert resumen["total_interacciones_procesadas"] == 2
    assert resumen["total_spam_detectado"] == 2
    assert resumen["distribucion_sentimientos"] == {}
    assert resumen["sentimiento_predominante"] is None
    assert resumen["sentimientos_predominantes"] == []


def test_resumen_conserva_compatibilidad_sin_campo_spam():
    resultados = [
        {
            "id": "legacy-001",
            "sentimiento": "neutral",
        },
    ]

    resumen = construir_resumen_comunidad(
        resultados=resultados,
        activos=[],
        fallos=[],
        total_pendientes=0,
    )

    assert resumen["total_spam_detectado"] == 0
    assert resumen["distribucion_sentimientos"] == {
        "neutral": 1,
    }
    assert resumen["sentimiento_predominante"] == "neutral"
