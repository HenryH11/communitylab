import pytest
from pydantic import ValidationError

from src.agentes.modelos import AnalisisMensaje


ANALISIS_BASE = {
    "sentimiento": "neutral",
    "tema_principal": "otros",
    "subtema": "Promoción de ingresos",
    "tipo_detectado": "comentario",
}


@pytest.mark.parametrize(
    "es_spam,motivo",
    [
        (False, None),
        (True, "Promesa de ingresos rápidos con captación privada"),
    ],
)
def test_modelo_spam_valido(es_spam, motivo):
    resultado = AnalisisMensaje.model_validate({
        **ANALISIS_BASE,
        "es_spam_detectado": es_spam,
        "motivo_spam": motivo,
    })

    assert resultado.es_spam_detectado is es_spam
    assert resultado.motivo_spam == motivo


@pytest.mark.parametrize(
    "es_spam,motivo",
    [
        (False, "Promoción sospechosa"),
        (True, None),
        (True, "   "),
    ],
)
def test_modelo_spam_rechaza_combinaciones_invalidas(es_spam, motivo):
    with pytest.raises(ValidationError):
        AnalisisMensaje.model_validate({
            **ANALISIS_BASE,
            "es_spam_detectado": es_spam,
            "motivo_spam": motivo,
        })


def test_modelo_spam_requiere_ambos_campos():
    with pytest.raises(ValidationError):
        AnalisisMensaje.model_validate(ANALISIS_BASE)


def test_spam_se_conserva_en_entrega_ds():
    from src.agentes.modelos import AnalisisLote
    from src.agentes.nodos.nodo_analizador import _campos_analisis
    from src.agentes.entrega_resultados import preparar_entrega_resultados

    predicciones = [
        {
            "id": "spam-001",
            "sentimiento": "neutral",
            "tema_principal": "otros",
            "subtema": "Oferta sospechosa",
            "tipo_detectado": "comentario",
            "es_spam_detectado": True,
            "motivo_spam": "Captación mediante oferta dudosa",
        },
        {
            "id": "normal-001",
            "sentimiento": "neutral",
            "tema_principal": "aprendizaje",
            "subtema": "Consulta educativa",
            "tipo_detectado": "pregunta_tecnica",
            "es_spam_detectado": False,
            "motivo_spam": None,
        },
    ]

    lote = AnalisisLote.model_validate({"resultados": predicciones})

    resultados = [
        {
            "id": item.id,
            "tipo_original": "comentario",
            "score_relevancia": 80,
            "elegible_contenido": True,
            "elegible_faq": False,
            **_campos_analisis(item),
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        }
        for item in lote.resultados
    ]

    entrega = preparar_entrega_resultados({
        "resultados": resultados,
        "pendientes": [],
        "ids_pendientes": [],
    })

    interacciones = {
        item["id"]: item
        for item in entrega["interacciones"]
    }

    assert interacciones["spam-001"]["es_spam_detectado"] is True
    assert interacciones["spam-001"]["motivo_spam"] == (
        "Captación mediante oferta dudosa"
    )

    assert interacciones["normal-001"]["es_spam_detectado"] is False
    assert interacciones["normal-001"]["motivo_spam"] is None

    assert all(
        item["tipo_original"] == "comentario"
        and item["score_relevancia"] == 80
        and item["elegible_contenido"] is True
        for item in interacciones.values()
    )
