"""Prueba real NVIDIA NIM -> análisis -> router determinista.

IMPORTANTE:
- realiza una llamada real a NVIDIA NIM;
- requiere NVIDIA_API_KEY;
- consume cuota;
- no forma parte de la suite pytest normal.
"""

from src.agentes.configuracion_ia import (
    PROVEEDOR_NVIDIA_NIM,
    VARIABLE_PROVEEDOR_ANALISIS,
)
from src.agentes.nodos.nodo_analizador import analizar_lote
from src.agentes.nodos.nodo_enrutador import determinar_rutas


def test_nvidia_analiza_y_el_router_conserva_logica_actual(
    monkeypatch,
):
    monkeypatch.setenv(
        VARIABLE_PROVEEDOR_ANALISIS,
        PROVEEDOR_NVIDIA_NIM,
    )

    estados = [
        {
            "id": "nvidia-router-001",
            "autor": "Ana",
            "canal": "#dudas-langgraph",
            "origen": "Discord_Grupo_ONE_G10",
            "idioma": "es",
            "texto": (
                "No entiendo cómo crear nodos condicionales "
                "en LangGraph. ¿Alguien podría ayudarme?"
            ),
            "tipo_original": "pregunta_tecnica",
            "score_relevancia": 80,
            "elegible_contenido": True,
            "elegible_faq": False,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        },
        {
            "id": "nvidia-router-002",
            "autor": "Bruno",
            "canal": "#feedback",
            "origen": "Discord_Grupo_ONE_G10",
            "idioma": "es",
            "texto": (
                "La plataforma se cae constantemente y "
                "deberían mejorar su estabilidad."
            ),
            "tipo_original": "feedback",
            "score_relevancia": 80,
            "elegible_contenido": True,
            "elegible_faq": False,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        },
        {
            "id": "nvidia-router-003",
            "autor": "Carla",
            "canal": "#logros-y-empleos",
            "origen": "Discord_Grupo_ONE_G10",
            "idioma": "es",
            "texto": (
                "Gracias al proyecto del curso conseguí "
                "mi primer trabajo como analista de datos."
            ),
            "tipo_original": "comentario",
            "score_relevancia": 90,
            "elegible_contenido": True,
            "elegible_faq": False,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        },
    ]

    analisis = analizar_lote(estados)

    resultados = []

    for estado, campos_analisis in zip(
        estados,
        analisis,
    ):
        estado_analizado = {
            **estado,
            **campos_analisis,
        }

        rutas = determinar_rutas(
            estado_analizado
        )

        resultado = {
            **estado_analizado,
            **rutas,
        }

        resultados.append(
            resultado
        )

    print()
    print("=" * 80)
    print("NVIDIA NIM -> ANALISIS -> ROUTER")
    print("=" * 80)

    for resultado in resultados:
        print()
        print(
            resultado["id"],
            "->",
            {
                "sentimiento": resultado["sentimiento"],
                "tema_principal": resultado["tema_principal"],
                "tipo_detectado": resultado["tipo_detectado"],
                "rutas": resultado["rutas"],
            },
        )

    por_id = {
        resultado["id"]: resultado
        for resultado in resultados
    }

    assert por_id["nvidia-router-001"]["tipo_detectado"] == (
        "pregunta_tecnica"
    )
    assert por_id["nvidia-router-001"]["rutas"] == [
        "preguntas_frecuentes"
    ]

    assert por_id["nvidia-router-002"]["tipo_detectado"] == "feedback"
    assert por_id["nvidia-router-002"]["rutas"] == [
        "insight_mejora"
    ]

    assert por_id["nvidia-router-003"]["tipo_detectado"] == "testimonio"
    assert por_id["nvidia-router-003"]["rutas"] == [
        "caso_exito",
        "boletin",
        "linkedin",
    ]