"""Prepara la salida estable de Data Science para otros componentes.

Entrada esperada:
    salida devuelta por `procesar_paquete_entrega()`.

Salida:
    estructura definida en `contrato_salida_ciencia_datos.py`, lista para
    serializarse como JSON y ser consumida por UI, OCI o reportes.

Este módulo no modifica el paquete de Data, no ejecuta Gemini y no persiste
archivos.
"""

from collections import Counter
from copy import deepcopy
import json

from src.agentes.contrato_salida_ciencia_datos import (
    ActivoEntregado,
    EntregaCienciaDatos,
    ResultadoInteraccion,
    TemaPrincipalResumen,
    VERSION_CONTRATO_SALIDA_DS,
)


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


def _validar_resultados(resultados: list[dict]) -> None:
    ids = []

    for resultado in resultados:
        identificador = resultado.get("id")

        if (
            not isinstance(identificador, str)
            or not identificador.strip()
            or identificador != identificador.strip()
        ):
            raise ValueError(
                "Cada resultado de Data Science debe tener un ID válido"
            )

        ids.append(identificador)

        rutas = resultado.get("rutas", [])
        activos = resultado.get("activos_generados", {})
        errores = resultado.get("errores", [])

        if not isinstance(rutas, list):
            raise ValueError(
                f"{identificador}: rutas debe ser una lista"
            )

        if not isinstance(activos, dict):
            raise ValueError(
                f"{identificador}: activos_generados debe ser un diccionario"
            )

        if not isinstance(errores, list):
            raise ValueError(
                f"{identificador}: errores debe ser una lista"
            )

        if not errores:
            for campo in (
                "sentimiento",
                "tema_principal",
                "subtema",
                "tipo_detectado",
            ):
                valor = resultado.get(campo)

                if not isinstance(valor, str) or not valor.strip():
                    raise ValueError(
                        f"{identificador}: falta el campo de análisis {campo}"
                    )

    if len(ids) != len(set(ids)):
        raise ValueError(
            "La salida de Data Science contiene IDs repetidos"
        )


def _ordenar_distribucion(contador: Counter) -> dict[str, int]:
    return {
        clave: cantidad
        for clave, cantidad in sorted(
            contador.items(),
            key=lambda item: (-item[1], item[0]),
        )
    }


def _obtener_sentimientos_predominantes(
    contador: Counter,
) -> list[str]:
    if not contador:
        return []

    maximo = max(contador.values())

    return sorted(
        sentimiento
        for sentimiento, cantidad in contador.items()
        if cantidad == maximo
    )


def _obtener_temas_principales(
    contador: Counter,
    limite: int = 3,
) -> list[TemaPrincipalResumen]:
    return [
        {
            "tema": tema,
            "cantidad": cantidad,
        }
        for tema, cantidad in sorted(
            contador.items(),
            key=lambda item: (-item[1], item[0]),
        )[:limite]
    ]


def _preparar_interaccion(
    resultado: dict,
) -> ResultadoInteraccion:
    interaccion: ResultadoInteraccion = {
        campo: deepcopy(resultado[campo])
        for campo in CAMPOS_INTERACCION
        if campo in resultado
    }
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

    _validar_resultados(resultados)

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

    sentimientos = Counter(
        resultado["sentimiento"]
        for resultado in resultados
        if isinstance(resultado.get("sentimiento"), str)
        and resultado["sentimiento"].strip()
    )

    temas = Counter(
        resultado["tema_principal"]
        for resultado in resultados
        if isinstance(resultado.get("tema_principal"), str)
        and resultado["tema_principal"].strip()
    )

    tipos_detectados = Counter(
        resultado["tipo_detectado"]
        for resultado in resultados
        if isinstance(resultado.get("tipo_detectado"), str)
        and resultado["tipo_detectado"].strip()
    )

    activos = _extraer_activos(
        resultados
    )

    total_con_activos = sum(
        bool(
            resultado.get(
                "activos_generados",
                {},
            )
        )
        for resultado in resultados
    )

    total_con_errores = sum(
        bool(
            resultado.get(
                "errores",
                [],
            )
        )
        for resultado in resultados
    )

    total_elegibles = sum(
        resultado.get(
            "elegible_contenido"
        ) is True
        for resultado in resultados
    )

    total_elegibles_faq = sum(
        resultado.get(
            "elegible_faq"
        ) is True
        for resultado in resultados
    )

    sentimientos_predominantes = (
        _obtener_sentimientos_predominantes(
            sentimientos
        )
    )

    sentimiento_predominante = (
        sentimientos_predominantes[0]
        if len(sentimientos_predominantes) == 1
        else None
    )

    interacciones = [
        _preparar_interaccion(
            resultado
        )
        for resultado in resultados
    ]

    return {
        "version_contrato": VERSION_CONTRATO_SALIDA_DS,
        "resumen_comunidad": {
            "total_interacciones_procesadas": len(
                resultados
            ),
            "total_pendientes": len(
                ids_pendientes
            ),
            "total_elegibles_contenido": total_elegibles,
            "total_elegibles_faq": total_elegibles_faq,
            "total_con_activos": total_con_activos,
            "total_activos_generados": len(
                activos
            ),
            "total_con_errores": total_con_errores,
            "sentimiento_predominante": (
                sentimiento_predominante
            ),
            "sentimientos_predominantes": (
                sentimientos_predominantes
            ),
            "distribucion_sentimientos": (
                _ordenar_distribucion(
                    sentimientos
                )
            ),
            "temas_principales": (
                _obtener_temas_principales(
                    temas
                )
            ),
            "distribucion_temas": (
                _ordenar_distribucion(
                    temas
                )
            ),
            "distribucion_tipos_detectados": (
                _ordenar_distribucion(
                    tipos_detectados
                )
            ),
        },
        "interacciones": interacciones,
        "activos": activos,
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
