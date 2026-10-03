"""
Prueba funcional del contrato de salida de Data Science.

Flujo validado:

Datos
    -> preparar_paquete_ia(...)
    -> procesar_paquete_entrega(...)
    -> preparar_entrega_resultados(...)
    -> contrato estructurado DS
    -> serialización JSON

La prueba NO imprime las 23 interacciones completas en terminal.
En su lugar, guarda la salida completa en UTF-8 dentro de `output/`
para evitar problemas de codificación y límites de la terminal.

IMPORTANTE:
- realiza llamadas reales a Gemini;
- requiere GEMINI_API_KEY configurada;
- consume cuota de API;
- se ejecuta de forma explícita porque el archivo comienza con `prueba_`.
"""

import json
from pathlib import Path

from scripts.apoyo_demostraciones import cargar_paquete_demostracion
from src.agentes.entrega_resultados import (
    entrega_resultados_a_json,
    preparar_entrega_resultados,
)
from src.agentes.grafo import procesar_paquete_entrega


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[2]
CARPETA_SALIDA = RAIZ_REPOSITORIO / "output"

RUTA_JSON_COMPLETO = (
    CARPETA_SALIDA
    / "entrega_ciencia_datos_completa.json"
)

RUTA_RESUMEN = (
    CARPETA_SALIDA
    / "resumen_entrega_ciencia_datos.txt"
)


def _guardar_resultados(
    entrega: dict,
    json_salida: str,
) -> None:
    """Guarda el contrato completo y un resumen legible en UTF-8."""
    CARPETA_SALIDA.mkdir(
        parents=True,
        exist_ok=True,
    )

    RUTA_JSON_COMPLETO.write_text(
        json_salida,
        encoding="utf-8",
    )

    resumen = entrega[
        "resumen_comunidad"
    ]

    lineas = [
        "RESUMEN DE ENTREGA DATA SCIENCE",
        "=" * 80,
        f"Version contrato: {entrega['version_contrato']}",
        (
            "Interacciones procesadas: "
            f"{resumen['total_interacciones_procesadas']}"
        ),
        (
            "Pendientes: "
            f"{resumen['total_pendientes']}"
        ),
        (
            "Elegibles para contenido: "
            f"{resumen['total_elegibles_contenido']}"
        ),
        (
            "Elegibles para FAQ: "
            f"{resumen['total_elegibles_faq']}"
        ),
        (
            "Interacciones con activos: "
            f"{resumen['total_con_activos']}"
        ),
        (
            "Activos individuales generados: "
            f"{resumen['total_activos_generados']}"
        ),
        (
            "Resultados con errores: "
            f"{resumen['total_con_errores']}"
        ),
        (
            "Sentimiento predominante: "
            f"{resumen['sentimiento_predominante']}"
        ),
        "",
        "DISTRIBUCION DE SENTIMIENTOS",
        "-" * 80,
    ]

    for sentimiento, cantidad in resumen[
        "distribucion_sentimientos"
    ].items():
        lineas.append(
            f"{sentimiento}: {cantidad}"
        )

    lineas.extend(
        [
            "",
            "TEMAS PRINCIPALES",
            "-" * 80,
        ]
    )

    for tema in resumen[
        "temas_principales"
    ]:
        lineas.append(
            f"{tema['tema']}: {tema['cantidad']}"
        )

    lineas.extend(
        [
            "",
            "INTERACCIONES CON ERRORES",
            "-" * 80,
        ]
    )

    interacciones_con_errores = [
        interaccion
        for interaccion in entrega["interacciones"]
        if interaccion.get("errores")
    ]

    if interacciones_con_errores:
        for interaccion in interacciones_con_errores:
            lineas.append(
                f"{interaccion['id']}: "
                f"{interaccion.get('errores', [])}"
            )
    else:
        lineas.append("Ninguna")

    RUTA_RESUMEN.write_text(
        "\n".join(lineas) + "\n",
        encoding="utf-8",
    )


def test_entrega_funcional_ciencia_datos():
    # --------------------------------------------------------------
    # 1. DATA PREPARA EL PAQUETE
    # --------------------------------------------------------------
    print()
    print("=" * 88)
    print("1. RECIBIENDO PAQUETE DESDE DATA")
    print("=" * 88)

    paquete = cargar_paquete_demostracion(
        tamano_ciclo=12,
    )

    print(
        "Estados recibidos desde Data:",
        len(paquete["estados"]),
    )
    print(
        "IDs pendientes desde Data:",
        len(paquete["plan"]["pendientes"]),
    )
    print(
        "IDs elegibles para contenido:",
        len(paquete["plan"]["ids_contenido"]),
    )

    # --------------------------------------------------------------
    # 2. DATA SCIENCE PROCESA EL PAQUETE
    # --------------------------------------------------------------
    print()
    print("=" * 88)
    print("2. EJECUTANDO DATA SCIENCE + GEMINI + LANGGRAPH")
    print("=" * 88)

    salida_ds = procesar_paquete_entrega(
        paquete
    )

    print(
        "Resultados internos DS:",
        len(salida_ds["resultados"]),
    )
    print(
        "Pendientes internos DS:",
        len(salida_ds["ids_pendientes"]),
    )

    # --------------------------------------------------------------
    # 3. CONSTRUIR CONTRATO DE SALIDA
    # --------------------------------------------------------------
    print()
    print("=" * 88)
    print("3. PREPARANDO CONTRATO DE SALIDA DATA SCIENCE")
    print("=" * 88)

    entrega = preparar_entrega_resultados(
        salida_ds
    )

    resumen = entrega[
        "resumen_comunidad"
    ]

    print(
        "Version contrato:",
        entrega["version_contrato"],
    )
    print(
        "Claves entregadas:",
        list(entrega.keys()),
    )

    # --------------------------------------------------------------
    # 4. SERIALIZAR A JSON Y GUARDAR RESULTADOS COMPLETOS
    # --------------------------------------------------------------
    print()
    print("=" * 88)
    print("4. SERIALIZANDO Y GUARDANDO SALIDA COMPLETA")
    print("=" * 88)

    json_salida = entrega_resultados_a_json(
        entrega
    )

    json_parseado = json.loads(
        json_salida
    )

    _guardar_resultados(
        entrega,
        json_salida,
    )

    print(
        "JSON generado correctamente:",
        len(json_salida),
        "caracteres",
    )
    print(
        "Salida completa:",
        RUTA_JSON_COMPLETO,
    )
    print(
        "Resumen:",
        RUTA_RESUMEN,
    )

    # --------------------------------------------------------------
    # 5. MOSTRAR SOLO RESUMEN EN TERMINAL
    # --------------------------------------------------------------
    print()
    print("=" * 88)
    print("5. RESUMEN DEL CONTRATO ENTREGADO")
    print("=" * 88)

    print(
        "Interacciones entregadas:",
        len(entrega["interacciones"]),
    )
    print(
        "Activos individuales entregados:",
        len(entrega["activos"]),
    )
    print(
        "Pendientes entregados:",
        len(entrega["ids_pendientes"]),
    )
    print(
        "Resultados con errores:",
        resumen["total_con_errores"],
    )
    print(
        "Sentimiento predominante:",
        resumen["sentimiento_predominante"],
    )
    print(
        "Temas principales:",
        [
            tema["tema"]
            for tema in resumen["temas_principales"]
        ],
    )

    # --------------------------------------------------------------
    # 6. VALIDACIONES FUNCIONALES DEL CONTRATO
    # --------------------------------------------------------------
    resultados_originales = salida_ds[
        "resultados"
    ]

    ids_resultados = {
        resultado["id"]
        for resultado in resultados_originales
    }

    ids_interacciones = {
        interaccion["id"]
        for interaccion in entrega["interacciones"]
    }

    ids_activos = {
        activo["id_interaccion"]
        for activo in entrega["activos"]
    }

    total_con_activos_esperado = sum(
        bool(
            resultado.get(
                "activos_generados",
                {},
            )
        )
        for resultado in resultados_originales
    )

    total_activos_esperado = sum(
        len(
            resultado.get(
                "activos_generados",
                {},
            )
        )
        for resultado in resultados_originales
    )

    total_con_errores_esperado = sum(
        bool(
            resultado.get(
                "errores",
                [],
            )
        )
        for resultado in resultados_originales
    )

    total_elegibles_faq_esperado = sum(
        resultado.get("elegible_faq") is True
        for resultado in resultados_originales
    )

    assert entrega[
        "version_contrato"
    ] == "1.1"

    assert resumen[
        "total_interacciones_procesadas"
    ] == len(resultados_originales)

    assert resumen[
        "total_pendientes"
    ] == len(
        salida_ds["ids_pendientes"]
    )

    assert resumen[
        "total_elegibles_faq"
    ] == total_elegibles_faq_esperado

    assert resumen[
        "total_con_activos"
    ] == total_con_activos_esperado

    assert resumen[
        "total_activos_generados"
    ] == total_activos_esperado

    assert resumen[
        "total_con_errores"
    ] == total_con_errores_esperado

    assert len(
        entrega["interacciones"]
    ) == len(
        resultados_originales
    )

    assert ids_interacciones == ids_resultados

    assert ids_activos.issubset(
        ids_resultados
    )

    assert entrega[
        "ids_pendientes"
    ] == salida_ds[
        "ids_pendientes"
    ]

    assert len(
        entrega["pendientes"]
    ) == len(
        salida_ds["pendientes"]
    )

    resultados_por_id = {
        resultado["id"]: resultado
        for resultado in resultados_originales
    }

    for interaccion in entrega["interacciones"]:
        resultado_original = resultados_por_id[
            interaccion["id"]
        ]

        assert "elegible_faq" in interaccion

        assert interaccion["elegible_faq"] is (
            resultado_original.get(
                "elegible_faq",
                False,
            )
        )

    # El contrato externo no expone detalles internos de DS.
    assert "resultados_por_id" not in entrega
    assert "ciclos" not in entrega
    assert "resultados" not in entrega

    # El JSON debe conservar exactamente el contenido del contrato.
    assert json_parseado == entrega

    # Los archivos generados deben existir y contener datos.
    assert RUTA_JSON_COMPLETO.exists()
    assert RUTA_JSON_COMPLETO.stat().st_size > 0

    assert RUTA_RESUMEN.exists()
    assert RUTA_RESUMEN.stat().st_size > 0

    print()
    print("=" * 88)
    print("RESULTADO FINAL")
    print("=" * 88)
    print("Contrato DS construido correctamente.")
    print(
        "Para revisar las 23 interacciones y todos los activos,"
    )
    print(
        "abre:",
        RUTA_JSON_COMPLETO,
    )
