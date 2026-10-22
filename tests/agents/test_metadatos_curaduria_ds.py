from unittest.mock import Mock, patch

import pytest

from src.agentes.modelos import (
    PublicacionLinkedIn,
    PublicacionLinkedInIA,
    InsightMejora,
    InsightMejoraIA,
)
from src.agentes.nodos import nodos_generadores
from src.app.curaduria_oci import validar_activo_curado


LINKEDIN = {
    "titulo": "Primer empleo en datos",
    "contenido": "Una persona compartió su primer empleo.",
    "hashtags": ["#Datos", "#Empleabilidad", "#Comunidad"],
}

INSIGHT = {
    "hallazgo": "Se reportan dificultades con la documentación.",
    "sugerencia_detectada": "Agregar ejemplos prácticos.",
}


def test_esquemas_ia_no_incluyen_metadatos():
    assert set(PublicacionLinkedInIA.model_json_schema()["properties"]) == {
        "titulo", "contenido", "hashtags"
    }
    assert set(InsightMejoraIA.model_json_schema()["properties"]) == {
        "hallazgo", "sugerencia_detectada"
    }


@pytest.mark.parametrize(
    "tipo,modelo,contenido",
    [
        (
            "linkedin",
            PublicacionLinkedIn,
            {**LINKEDIN, "canal_recomendado": "LinkedIn Oficial"},
        ),
        (
            "insight_mejora",
            InsightMejora,
            {**INSIGHT, "area": "aprendizaje"},
        ),
        ("linkedin", PublicacionLinkedIn, LINKEDIN),
        ("insight_mejora", InsightMejora, INSIGHT),
    ],
)
def test_curaduria_acepta_activos_actuales_e_historicos(
    tipo, modelo, contenido
):
    assert modelo.model_validate(contenido).model_dump() == contenido
    validar_activo_curado(tipo, contenido)


def test_nodo_generador_entrega_activos_aprobables():
    generadores = {
        "linkedin": Mock(),
        "insight_mejora": Mock(),
    }

    generadores["linkedin"].invoke.return_value = PublicacionLinkedInIA(
        **LINKEDIN
    )
    generadores["insight_mejora"].invoke.return_value = InsightMejoraIA(
        **INSIGHT
    )

    estado = {
        "id": "int-prueba",
        "autor": "Persona de prueba",
        "texto": "Sería útil mejorar los ejemplos.",
        "tema_principal": "aprendizaje",
        "subtema": "ejemplos prácticos",
        "tipo_detectado": "feedback",
        "rutas": ["linkedin", "insight_mejora"],
        "errores": [],
        "fallos": [],
    }

    with (
        patch.object(
            nodos_generadores,
            "obtener_proveedor_generacion",
            return_value="gemini",
        ),
        patch.object(
            nodos_generadores,
            "_obtener_generadores",
            return_value=generadores,
        ),
    ):
        salida = nodos_generadores.generar_activos(estado)

    assert salida["errores"] == []
    assert salida["fallos"] == []

    activos = salida["activos_generados"]

    assert activos["linkedin"]["canal_recomendado"] == "LinkedIn Oficial"
    assert activos["insight_mejora"]["area"] == "aprendizaje"

    for tipo, contenido in activos.items():
        validar_activo_curado(tipo, contenido)
