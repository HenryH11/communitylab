"""Prueba real de generación multiruta utilizando NVIDIA NIM.

IMPORTANTE:
- realiza llamadas reales a NVIDIA NIM;
- requiere NVIDIA_API_KEY;
- consume cuota;
- no forma parte de la suite pytest normal.
"""

from src.agentes.configuracion_ia import (
    PROVEEDOR_NVIDIA_NIM,
    VARIABLE_PROVEEDOR_GENERACION,
)
from src.agentes.nodos.nodos_generadores import generar_activos


def test_nvidia_genera_multiples_activos_independientes(
    monkeypatch,
):
    monkeypatch.setenv(
        VARIABLE_PROVEEDOR_GENERACION,
        PROVEEDOR_NVIDIA_NIM,
    )

    estado = {
        "id": "nvidia-multiruta-001",
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

        # Resultado previo del análisis
        "sentimiento": "muy_positivo",
        "tema_principal": "empleabilidad",
        "subtema": "primer trabajo analista de datos",
        "tipo_detectado": "testimonio",

        # Resultado previo del router
        "rutas": [
            "caso_exito",
            "boletin",
            "linkedin",
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
    print("NVIDIA NIM - GENERACIÓN MULTIRUTA")
    print("=" * 80)

    for ruta, activo in resultado[
        "activos_generados"
    ].items():
        print()
        print(ruta)
        print(activo)

    if resultado.get("errores"):
        print()
        print("ERRORES")
        print(resultado["errores"])

    if resultado.get("fallos"):
        print()
        print("FALLOS")
        print(resultado["fallos"])

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
        "caso_exito",
        "boletin",
        "linkedin",
    }

    caso_exito = activos[
        "caso_exito"
    ]

    assert caso_exito["titular"].strip()
    assert caso_exito["resumen"].strip()

    boletin = activos[
        "boletin"
    ]

    assert boletin["seccion"].strip()
    assert boletin["titular"].strip()
    assert boletin["resumen"].strip()

    linkedin = activos[
        "linkedin"
    ]

    assert linkedin["titulo"].strip()
    assert linkedin["contenido"].strip()

    assert 3 <= len(
        linkedin["hashtags"]
    ) <= 4

    assert linkedin[
        "canal_recomendado"
    ] == "LinkedIn Oficial"