"""Prueba real aislada de NVIDIA NIM con salida JSON + Pydantic.

IMPORTANTE:
- realiza una llamada real a NVIDIA NIM;
- requiere NVIDIA_API_KEY;
- consume cuota;
- no forma parte de la suite pytest normal porque comienza con `prueba_`.
"""

import json

from src.agentes.modelos import AnalisisMensaje
from src.agentes.prompts.analisis import template_analisis
from src.agentes.proveedores.nvidia_nim import obtener_modelo_nvidia


def test_nvidia_nim_devuelve_analisis_estructurado():
    modelo = obtener_modelo_nvidia()

    # Adaptación técnica específica de NVIDIA:
    # solicitamos JSON al endpoint y luego dejamos que
    # Pydantic valide el contrato de CommunityLab.
    modelo_json = modelo.bind(
        response_format={
            "type": "json_object",
        }
    )

    cadena = template_analisis | modelo_json

    respuesta = cadena.invoke(
        {
            "origen": "Discord_Grupo_ONE_G10",
            "canal": "#dudas-langgraph",
            "idioma": "es",
            "tipo_original": "pregunta_tecnica",
            "texto": (
                "No entiendo cómo crear nodos condicionales "
                "en LangGraph. ¿Alguien podría ayudarme?"
            ),
        }
    )

    assert isinstance(respuesta.content, str)
    assert respuesta.content.strip()

    datos = json.loads(
        respuesta.content
    )

    analisis = AnalisisMensaje.model_validate(
        datos
    )

    print()
    print("=" * 80)
    print("NVIDIA NIM - RESPUESTA ESTRUCTURADA")
    print("=" * 80)
    print(
        analisis.model_dump_json(
            indent=2
        )
    )

    assert analisis.sentimiento in {
        "muy_positivo",
        "positivo",
        "neutral",
        "negativo",
        "muy_negativo",
    }

    assert analisis.tema_principal in {
        "empleabilidad",
        "aprendizaje",
        "programacion",
        "datos_ia",
        "plataforma",
        "comunidad",
        "mentoria",
        "cloud_infraestructura",
        "certificacion",
        "programa_hackathon",
        "otros",
    }

    assert analisis.tipo_detectado in {
        "testimonio",
        "pregunta_tecnica",
        "pregunta_programa",
        "feedback",
        "comentario",
    }

    assert analisis.subtema.strip()