"""Prepara la salida estable de Data Science para otros componentes.

Entrada esperada:
    salida devuelta por `procesar_paquete_entrega()`.

Salida:
    estructura definida en `contrato_salida_ciencia_datos.py`, lista para
    serializarse como JSON y ser consumida por UI, OCI o reportes.

Este módulo no modifica el paquete de Data, no ejecuta Gemini y no persiste
archivos.
"""

from copy import deepcopy
import json
from typing import cast

from src.agentes.contrato_salida_ciencia_datos import (
    ActivoEntregado,
    EntregaCienciaDatos,
    ResultadoInteraccion,
    VERSION_CONTRATO_SALIDA_DS,
)
from src.agentes.resumen_entrega import construir_resumen_comunidad
from src.agentes.validacion_entrega import validar_resultados


CAMPOS_INTERACCION = (
    "id",
    "autor",
    "canal",
    "origen",
    "idioma",
    "texto",
    "tipo_original",
    "score_relevancia",
    "elegible_contenido",
    "elegible_faq",
    "sentimiento",
    "tema_principal",
    "subtema",
    "tipo_detectado",
)


def _preparar_interaccion(
    resultado: dict,
) -> ResultadoInteraccion:
    interaccion = cast(
        ResultadoInteraccion,
        {
            campo: deepcopy(resultado[campo])
            for campo in CAMPOS_INTERACCION
            if campo in resultado
        },
    )
    interaccion["elegible_faq"] = resultado.get(
        "elegible_faq",
        False,
    )
    interaccion["rutas"] = deepcopy(
        resultado.get("rutas", [])
    )
    interaccion["activos_generados"] = deepcopy(
        resultado.get("activos_generados", {})
    )
    interaccion["errores"] = deepcopy(
        resultado.get("errores", [])
    )
    interaccion["fallos"] = deepcopy(
        resultado.get("fallos", [])
    )

    return interaccion


def _extraer_activos(
    resultados: list[dict],
) -> list[ActivoEntregado]:
    activos: list[ActivoEntregado] = []

    for resultado in resultados:
        identificador = resultado["id"]

        for tipo, contenido in resultado.get(
            "activos_generados",
            {},
        ).items():
            activos.append(
                {
                    "id_interaccion": identificador,
                    "tipo": tipo,
                    "contenido": deepcopy(contenido),
                }
            )

    return activos


def preparar_entrega_resultados(
    salida_procesamiento: dict,
) -> EntregaCienciaDatos:
    """Convierte la salida interna de DS en el contrato estable de entrega."""
    if not isinstance(salida_procesamiento, dict):
        raise TypeError(
            "salida_procesamiento debe ser un diccionario"
        )

    resultados = salida_procesamiento.get(
        "resultados"
    )
    pendientes = salida_procesamiento.get(
        "pendientes"
    )
    ids_pendientes = salida_procesamiento.get(
        "ids_pendientes"
    )

    if not isinstance(resultados, list):
        raise ValueError(
            "La salida debe contener resultados como lista"
        )

    if not isinstance(pendientes, list):
        raise ValueError(
            "La salida debe contener pendientes como lista"
        )

    if not isinstance(ids_pendientes, list):
        raise ValueError(
            "La salida debe contener ids_pendientes como lista"
        )

    validar_resultados(resultados)

    ids_resultados = {
        resultado["id"]
        for resultado in resultados
    }

    if len(ids_pendientes) != len(set(ids_pendientes)):
        raise ValueError(
            "ids_pendientes contiene IDs repetidos"
        )

    if ids_resultados.intersection(ids_pendientes):
        raise ValueError(
            "Un ID no puede estar procesado y pendiente al mismo tiempo"
        )

    activos = _extraer_activos(
        resultados
    )
    fallos = [
        deepcopy(fallo)
        for resultado in resultados
        for fallo in resultado.get("fallos", [])
    ]
    ids_reintentables = list(
        dict.fromkeys(
            fallo["id"]
            for fallo in fallos
            if fallo.get("reintentable") is True
        )
    )

    interacciones = [
        _preparar_interaccion(
            resultado
        )
        for resultado in resultados
    ]

    return {
        "version_contrato": VERSION_CONTRATO_SALIDA_DS,
        "id_ejecucion": salida_procesamiento.get("id_ejecucion"),
        "resumen_comunidad": construir_resumen_comunidad(
            resultados,
            activos,
            fallos,
            len(ids_pendientes),
        ),
        "interacciones": interacciones,
        "activos": activos,
        "fallos": fallos,
        "ids_reintentables": ids_reintentables,
        "pendientes": deepcopy(
            pendientes
        ),
        "ids_pendientes": deepcopy(
            ids_pendientes
        ),
    }


def entrega_resultados_a_json(
    entrega: EntregaCienciaDatos,
    *,
    indentacion: int = 2,
) -> str:
    """Serializa el contrato de salida sin escribir archivos."""
    return json.dumps(
        entrega,
        ensure_ascii=False,
        indent=indentacion,
    )
