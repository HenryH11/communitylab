"""Prueba real de generación de una FAQ utilizando NVIDIA NIM.

IMPORTANTE:
- realiza una llamada real a NVIDIA NIM;
- requiere NVIDIA_API_KEY;
- consume cuota;
- no forma parte de la suite pytest normal.
"""

from src.agentes.configuracion_ia import (
    PROVEEDOR_NVIDIA_NIM,
    VARIABLE_PROVEEDOR_GENERACION,
)
from src.agentes.nodos.nodos_generadores import (
    generar_activos,
)


def test_nvidia_genera_faq_estructurada(
    monkeypatch,
):
    monkeypatch.setenv(
        VARIABLE_PROVEEDOR_GENERACION,
        PROVEEDOR_NVIDIA_NIM,
    )

    estado = {
        "id": "nvidia-faq-001",
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

        # Resultado previo del análisis
        "sentimiento": "neutral",
        "tema_principal": "datos_ia",
        "subtema": "nodos de LangGraph",
        "tipo_detectado": "pregunta_tecnica",

        # Ruta ya determinada
        "rutas": [
            "preguntas_frecuentes",
        ],

        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }

    resultado = generar_activos(
        estado
    )

    print()
    print("=" * 80)
    print("NVIDIA NIM - GENERACIÓN FAQ")
    print("=" * 80)
    print(resultado)

    assert resultado.get(
        "errores",
        [],
    ) == []

    assert resultado.get(
        "fallos",
        [],
    ) == []

    activos = resultado[
        "activos_generados"
    ]

    assert set(activos) == {
        "preguntas_frecuentes"
    }

    faq = activos[
        "preguntas_frecuentes"
    ]

    assert isinstance(
        faq["tema"],
        str,
    )
    assert faq["tema"].strip()

    assert isinstance(
        faq["respuesta"],
        str,
    )
    assert faq["respuesta"].strip()