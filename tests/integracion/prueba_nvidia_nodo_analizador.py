"""Prueba real del nodo analizador utilizando NVIDIA NIM.

IMPORTANTE:
- realiza una llamada real a NVIDIA NIM;
- requiere NVIDIA_API_KEY;
- consume cuota;
- no pertenece a la suite pytest normal.
"""

from src.agentes.configuracion_ia import (
    PROVEEDOR_NVIDIA_NIM,
    VARIABLE_PROVEEDOR_ANALISIS,
)
from src.agentes.nodos.nodo_analizador import (
    analizar_mensaje,
)


def test_nodo_analizador_funciona_con_nvidia(
    monkeypatch,
):
    monkeypatch.setenv(
        VARIABLE_PROVEEDOR_ANALISIS,
        PROVEEDOR_NVIDIA_NIM,
    )

    estado = {
        "id": "nvidia-prueba-001",
        "autor": "Usuario de prueba",
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
    }

    resultado = analizar_mensaje(
        estado
    )

    print()
    print("=" * 80)
    print("NVIDIA NIM - NODO ANALIZADOR")
    print("=" * 80)
    print(resultado)

    assert resultado.get("errores", []) == []
    assert resultado.get("fallos", []) == []

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