from typing import cast

import pytest

from src.agentes.estado_agente import EstadoAgente
from src.agentes.modelos import AnalisisMensaje
from src.agentes.nodos.nodo_enrutador import determinar_rutas
from src.agentes.entrega_resultados import preparar_entrega_resultados


@pytest.mark.parametrize(
    "texto,tipo,es_spam,motivo,rutas_esperadas",
    [
        (
            "Gana 500 dólares diarios sin experiencia. Escríbeme al privado.",
            "comentario",
            True,
            "Promesa de ingresos rápidos con captación privada",
            [],
        ),
        (
            "Cuidado con el mensaje que promete 500 dólares diarios. Es una estafa.",
            "comentario",
            False,
            None,
            [],
        ),
        (
            "Conseguí mi primer empleo como analista con un salario de 2500 soles.",
            "testimonio",
            False,
            None,
            ["caso_exito", "boletin", "linkedin"],
        ),
        (
            "¿Cuánto cuesta el examen OCI y los servicios cloud?",
            "pregunta_tecnica",
            False,
            None,
            ["preguntas_frecuentes"],
        ),
    ],
)
def test_casos_aceptacion_estructurales(
    texto, tipo, es_spam, motivo, rutas_esperadas
):
    # Simulamos una clasificación ya obtenida.
    # NO estamos evaluando la capacidad semántica del LLM.
    prediccion = AnalisisMensaje.model_validate({
        "sentimiento": "positivo" if tipo == "testimonio" else "neutral",
        "tema_principal": "otros",
        "subtema": "Caso de aceptación",
        "tipo_detectado": tipo,
        "es_spam_detectado": es_spam,
        "motivo_spam": motivo,
    })

    estado: EstadoAgente = cast(EstadoAgente, {
        "id": "caso-prueba",
        "texto": texto,
        **prediccion.model_dump(),
        "score_relevancia": 90,
        "elegible_contenido": True,
        "elegible_faq": False,
    })

    assert prediccion.es_spam_detectado is es_spam
    assert determinar_rutas(estado)["rutas"] == rutas_esperadas


def test_duplicacion_sigue_siendo_responsabilidad_de_data():
    texto = "Gana 500 dólares diarios. Escríbeme al privado."

    def construir_resultado(identificador):
        return {
            "id": identificador,
            "autor": "mismo-autor",
            "texto": texto,
            "tipo_original": "comentario",
            "score_relevancia": 90,
            "elegible_contenido": True,
            "elegible_faq": False,
            "sentimiento": "neutral",
            "tema_principal": "otros",
            "subtema": "Oferta dudosa",
            "tipo_detectado": "comentario",
            "es_spam_detectado": True,
            "motivo_spam": "Captación mediante oferta dudosa",
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        }

    entrega = preparar_entrega_resultados({
        "resultados": [
            construir_resultado("caso-01"),
            construir_resultado("caso-05"),
        ],
        "pendientes": [],
        "ids_pendientes": [],
    })

    assert len(entrega["interacciones"]) == 2
    assert [x["id"] for x in entrega["interacciones"]] == [
        "caso-01",
        "caso-05",
    ]
    assert entrega["resumen_comunidad"]["total_spam_detectado"] == 2
