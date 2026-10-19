"""
Prueba E2E real del contrato Datos -> Data Science.

Esta prueba toma el paquete completo preparado por el módulo real de Datos,
procesa todos los estados planificados con el consumidor de Data Science y
muestra, para cada interacción:

- entrada recibida desde Datos;
- análisis realizado por Gemini;
- resultado del routing de LangGraph;
- activos generados;
- errores.

IMPORTANTE:
- realiza llamadas reales a Gemini;
- requiere conexión a Internet;
- requiere GEMINI_API_KEY disponible en el .env del proyecto;
- consume cuota de API;
- al llamarse `prueba_...` no entra automáticamente en la suite normal
  de pytest; debe ejecutarse de forma explícita.
"""

from collections import Counter

from scripts.apoyo_demostraciones import (
    cargar_paquete_demostracion,
    obtener_evaluaciones_por_id,
)
from src.agentes.grafo import procesar_paquete_entrega


TAMANO_CICLO = 12

SENTIMIENTOS_VALIDOS = {
    "muy_positivo",
    "positivo",
    "neutral",
    "negativo",
    "muy_negativo",
}

CAMPOS_ANALISIS_REQUERIDOS = {
    "sentimiento",
    "tema_principal",
    "subtema",
    "tipo_detectado",
    "rutas",
    "activos_generados",
}


def _imprimir_titulo(texto: str, caracter: str = "=") -> None:
    print()
    print(caracter * 88)
    print(texto)
    print(caracter * 88)


def _imprimir_activos(activos: dict) -> None:
    if not activos:
        print("Ninguno")
        return

    for ruta, activo in activos.items():
        print()
        print(f"[{ruta}]")

        if isinstance(activo, dict):
            for clave, valor in activo.items():
                print(f"{clave}: {valor}")
        else:
            print(activo)


def test_paquete_completo_datos_a_ciencia_datos():
    """
    Ejecuta el flujo completo sobre todas las entradas planificadas por Datos:

    JSON simulado
        -> preparar_paquete_ia()
        -> paquete Datos -> DS
        -> procesar_paquete_entrega()
        -> Gemini
        -> análisis estructurado
        -> LangGraph
        -> routing
        -> generación de activos
        -> resultado final por ID
    """

    # ------------------------------------------------------------------
    # 1. RECIBIR EL PAQUETE DESDE EL MÓDULO REAL DE DATOS
    # ------------------------------------------------------------------

    paquete = cargar_paquete_demostracion(
        tamano_ciclo=TAMANO_CICLO,
    )

    estados = paquete["estados"]
    plan = paquete["plan"]

    estados_por_id = {
        estado["id"]: estado
        for estado in estados
    }

    evaluaciones_por_id = obtener_evaluaciones_por_id(
        paquete["informe"]
    )

    ids_contenido = set(
        plan["ids_contenido"]
    )

    ids_planificados = [
        identificador
        for ciclo in plan["ciclos"]
        for identificador in ciclo["ids"]
    ]

    _imprimir_titulo(
        "PAQUETE RECIBIDO DE DATOS"
    )

    print(
        "Estados recibidos:",
        len(estados),
    )
    print(
        "Ciclos planificados:",
        [
            (ciclo["indice"], len(ciclo["ids"]))
            for ciclo in plan["ciclos"]
        ],
    )
    print(
        "IDs planificados:",
        len(ids_planificados),
    )
    print(
        "IDs pendientes:",
        len(plan["pendientes"]),
    )
    print(
        "IDs elegibles para contenido:",
        len(ids_contenido),
    )

    # ------------------------------------------------------------------
    # 2. EJECUTAR EL CONSUMIDOR COMPLETO DE DATA SCIENCE
    # ------------------------------------------------------------------

    _imprimir_titulo(
        "EJECUTANDO DATA SCIENCE + GEMINI + LANGGRAPH"
    )

    salida = procesar_paquete_entrega(
        paquete
    )

    resultados = salida["resultados"]
    resultados_por_id = salida[
        "resultados_por_id"
    ]

    # ------------------------------------------------------------------
    # 3. MOSTRAR ENTRADA -> RESULTADO PARA CADA INTERACCIÓN
    # ------------------------------------------------------------------

    conteo_sentimientos = Counter()
    conteo_temas = Counter()
    conteo_tipos_detectados = Counter()
    conteo_rutas = Counter()
    conteo_activos = Counter()

    ids_con_errores = []
    ids_con_activos = []
    problemas_estructurales = []

    for numero, estado in enumerate(
        estados,
        start=1,
    ):
        mensaje_id = estado["id"]

        _imprimir_titulo(
            f"INTERACCIÓN {numero}/{len(estados)}: {mensaje_id}"
        )

        print("ENTRADA RECIBIDA DE DATOS")
        print("-" * 88)

        print(
            "Autor:",
            estado.get("autor"),
        )
        print(
            "Canal:",
            estado.get("canal"),
        )
        print(
            "Origen:",
            estado.get("origen"),
        )
        print(
            "Idioma:",
            estado.get("idioma"),
        )
        print(
            "Texto:",
            estado.get("texto"),
        )
        print(
            "Tipo original:",
            estado.get("tipo_original"),
        )
        print(
            "Score relevancia:",
            estado.get("score_relevancia"),
        )

        evaluacion = evaluaciones_por_id.get(
            mensaje_id,
            {},
        )

        print(
            "Incluido sentimiento:",
            evaluacion.get(
                "incluido_sentimiento"
            ),
        )
        print(
            "Elegible contenido:",
            mensaje_id in ids_contenido,
        )
        print(
            "Desglose relevancia:",
            evaluacion.get("desglose"),
        )

        resultado = resultados_por_id.get(
            mensaje_id
        )

        if resultado is None:
            print()
            print(
                "RESULTADO DATA SCIENCE: "
                "NO ENCONTRADO"
            )
            problemas_estructurales.append(
                f"{mensaje_id}: no existe resultado"
            )
            continue

        print()
        print("RESULTADO DATA SCIENCE")
        print("-" * 88)

        sentimiento = resultado.get(
            "sentimiento"
        )
        tema_principal = resultado.get(
            "tema_principal"
        )
        subtema = resultado.get(
            "subtema"
        )
        tipo_detectado = resultado.get(
            "tipo_detectado"
        )
        rutas = resultado.get(
            "rutas",
            [],
        )
        activos = resultado.get(
            "activos_generados",
            {},
        )
        errores = resultado.get(
            "errores",
            [],
        )

        if not isinstance(errores, list):
            problemas_estructurales.append(
                f"{mensaje_id}: errores debe ser una lista"
            )

        print(
            "Sentimiento:",
            sentimiento,
        )
        print(
            "Tema principal:",
            tema_principal,
        )
        print(
            "Subtema:",
            subtema,
        )
        print(
            "Tipo detectado:",
            tipo_detectado,
        )

        print()
        print("ENRUTAMIENTO LANGGRAPH")
        print("-" * 88)
        print(
            "Rutas:",
            rutas,
        )

        print()
        print("ACTIVOS GENERADOS")
        print("-" * 88)
        _imprimir_activos(
            activos
        )

        print()
        print("ERRORES")
        print("-" * 88)
        print(
            errores
            if errores
            else "[]"
        )

        # --------------------------------------------------------------
        # Acumuladores para el resumen final.
        # --------------------------------------------------------------

        if sentimiento:
            conteo_sentimientos[
                sentimiento
            ] += 1

        if tema_principal:
            conteo_temas[
                tema_principal
            ] += 1

        if tipo_detectado:
            conteo_tipos_detectados[
                tipo_detectado
            ] += 1

        for ruta in rutas:
            conteo_rutas[ruta] += 1

        for nombre_activo in activos:
            conteo_activos[
                nombre_activo
            ] += 1

        if activos:
            ids_con_activos.append(
                mensaje_id
            )

        if errores:
            ids_con_errores.append(
                mensaje_id
            )

        # --------------------------------------------------------------
        # Validaciones por interacción.
        # --------------------------------------------------------------

        faltantes = (
            CAMPOS_ANALISIS_REQUERIDOS
            - resultado.keys()
        )

        if faltantes:
            problemas_estructurales.append(
                f"{mensaje_id}: faltan campos "
                f"{sorted(faltantes)}"
            )

        if (
            resultado.get("tipo_original")
            != estado.get("tipo_original")
        ):
            problemas_estructurales.append(
                f"{mensaje_id}: tipo_original "
                "no fue preservado"
            )

        if (
            resultado.get("score_relevancia")
            != estado.get("score_relevancia")
        ):
            problemas_estructurales.append(
                f"{mensaje_id}: score_relevancia "
                "no fue preservado"
            )

        if (
            sentimiento
            not in SENTIMIENTOS_VALIDOS
        ):
            problemas_estructurales.append(
                f"{mensaje_id}: sentimiento "
                f"inválido {sentimiento!r}"
            )

        if not isinstance(
            tema_principal,
            str,
        ) or not tema_principal.strip():
            problemas_estructurales.append(
                f"{mensaje_id}: tema_principal vacío"
            )

        if not isinstance(
            subtema,
            str,
        ) or not subtema.strip():
            problemas_estructurales.append(
                f"{mensaje_id}: subtema vacío"
            )

        if not isinstance(
            tipo_detectado,
            str,
        ) or not tipo_detectado.strip():
            problemas_estructurales.append(
                f"{mensaje_id}: tipo_detectado vacío"
            )

        # La relevancia decide generación de contenido,
        # no si el mensaje recibe análisis de sentimiento.
        if mensaje_id not in ids_contenido:
            if rutas:
                problemas_estructurales.append(
                    f"{mensaje_id}: no elegible para "
                    "contenido pero recibió rutas"
                )

            if activos:
                problemas_estructurales.append(
                    f"{mensaje_id}: no elegible para "
                    "contenido pero generó activos"
                )

    # ------------------------------------------------------------------
    # 4. RESUMEN CONSOLIDADO DE LA EJECUCIÓN
    # ------------------------------------------------------------------

    _imprimir_titulo(
        "RESUMEN FINAL DATA -> DATA SCIENCE"
    )

    print(
        "Estados recibidos de Datos:",
        len(estados),
    )
    print(
        "Estados procesados por DS:",
        len(resultados),
    )
    print(
        "Estados pendientes:",
        len(salida["ids_pendientes"]),
    )
    print(
        "Elegibles para contenido:",
        len(ids_contenido),
    )
    print(
        "Con activos generados:",
        len(ids_con_activos),
    )
    print(
        "Con errores:",
        len(ids_con_errores),
    )

    print()
    print(
        "Distribución de sentimientos:",
        dict(conteo_sentimientos),
    )
    print(
        "Distribución de temas:",
        dict(conteo_temas),
    )
    print(
        "Tipos detectados:",
        dict(conteo_tipos_detectados),
    )
    print(
        "Rutas ejecutadas:",
        dict(conteo_rutas),
    )
    print(
        "Activos generados:",
        dict(conteo_activos),
    )

    if ids_con_activos:
        print(
            "IDs con activos:",
            ids_con_activos,
        )

    if ids_con_errores:
        print(
            "IDs con errores:",
            ids_con_errores,
        )

    if problemas_estructurales:
        print()
        print("PROBLEMAS ESTRUCTURALES")
        print("-" * 88)

        for problema in problemas_estructurales:
            print(
                "-",
                problema,
            )

    # ------------------------------------------------------------------
    # 5. ASSERTS E2E
    # ------------------------------------------------------------------

    assert len(estados) == 23
    assert len(ids_planificados) == 23
    assert plan["pendientes"] == []

    assert len(resultados) == len(estados)

    assert set(
        resultados_por_id
    ) == set(
        estados_por_id
    )

    assert salida[
        "ids_pendientes"
    ] == []

    assert len(
        salida["ciclos"]
    ) == len(
        plan["ciclos"]
    )

    assert not problemas_estructurales, (
        "Se detectaron problemas estructurales:\n- "
        + "\n- ".join(
            problemas_estructurales
        )
    )

    assert not ids_con_errores, (
        "Se encontraron errores de ejecución "
        f"en los IDs: {ids_con_errores}"
    )
