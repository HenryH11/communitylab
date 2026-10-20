"""Prueba real de análisis por lotes utilizando NVIDIA NIM.

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
from src.agentes.nodos.nodo_analizador import (
    analizar_lote,
)


def test_nvidia_nim_analiza_lote_sin_perder_resultados(
    monkeypatch,
):
    monkeypatch.setenv(
        VARIABLE_PROVEEDOR_ANALISIS,
        PROVEEDOR_NVIDIA_NIM,
    )

    estados = [
        {
            "id": "nvidia-lote-001",
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
            "id": "nvidia-lote-002",
            "autor": "Bruno",
            "canal": "#feedback",
            "origen": "Discord_Grupo_ONE_G10",
            "idioma": "es",
            "texto": (
                "La plataforma se cae bastante y deberían "
                "mejorar su estabilidad."
            ),
            "tipo_original": "feedback",
            "score_relevancia": 75,
            "elegible_contenido": True,
            "elegible_faq": False,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        },
        {
            "id": "nvidia-lote-003",
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

    resultados = analizar_lote(
        estados
    )

    print()
    print("=" * 80)
    print("NVIDIA NIM - ANÁLISIS POR LOTES")
    print("=" * 80)

    for estado, resultado in zip(
        estados,
        resultados,
    ):
        print()
        print(
            estado["id"],
            "->",
            resultado,
        )

    assert len(resultados) == len(estados)

    for resultado in resultados:
        assert resultado.get(
            "errores",
            [],
        ) == []

        assert resultado.get(
            "fallos",
            [],
        ) == []

        assert resultado["sentimiento"] in {
            "muy_positivo",
            "positivo",
            "neutral",
            "negativo",
            "muy_negativo",
        }

        assert resultado["tipo_detectado"] in {
            "testimonio",
            "pregunta_tecnica",
            "pregunta_programa",
            "feedback",
            "comentario",
        }

        assert resultado["tema_principal"]
        assert resultado["subtema"]