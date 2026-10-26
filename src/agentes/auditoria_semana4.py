"""Construcción del paquete de evidencia para la auditoría de Semana 4.

Este módulo NO modifica el contrato productivo de Data Science.

Combina:
- entrada original;
- decisiones de Data;
- salida normal de Data Science;
- eventos de observabilidad;
- configuración efectiva de IA;
- metadatos reproducibles de la ejecución.

El resultado está pensado exclusivamente como evidencia para auditoría.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any
from src.agentes.entrega_resultados import preparar_entrega_resultados

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
    obtener_configuracion_enrutamiento,
    obtener_proveedor_analisis,
    obtener_proveedor_generacion,
)
from src.agentes.proveedores.gemini import MODELO_GEMINI


VERSION_AUDITORIA_SEMANA4 = "1.2"


def capturar_configuracion_ia_auditoria() -> dict[str, Any]:
    """Captura la configuración efectiva que debe acompañar la ejecución."""

    enrutamiento = obtener_configuracion_enrutamiento()

    modelos_nvidia_por_tier = {
        tier: datos["modelo_nvidia"]
        for tier, datos in enrutamiento["tiers"].items()
    }

    return {
        "proveedor_analisis": obtener_proveedor_analisis(),
        "proveedor_generacion": obtener_proveedor_generacion(),
        "enrutamiento_adaptativo_activo": enrutamiento[
            "enrutamiento_adaptativo_activo"
        ],
        "modelos_nvidia_por_tier": modelos_nvidia_por_tier,
        "modelo_gemini": MODELO_GEMINI,
    }


def cargar_eventos_observabilidad(
    ruta_log: str | Path,
    *,
    id_ejecucion: str,
) -> list[dict]:
    """Carga los eventos de proveedor correspondientes a una ejecución."""

    ruta = Path(ruta_log)

    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe el archivo de observabilidad: {ruta}"
        )

    eventos: list[dict] = []

    with ruta.open("r", encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()

            if not linea:
                continue

            try:
                evento = json.loads(linea)
            except json.JSONDecodeError as error:
                raise ValueError(
                    "El log de observabilidad contiene JSON inválido "
                    f"en la línea {numero_linea}."
                ) from error

            if evento.get("id_ejecucion") != id_ejecucion:
                continue

            if evento.get("evento") != "proveedor_ia_resuelto":
                continue

            eventos.append(evento)

    return eventos


def _indexar_entrada(datos_fuente: dict) -> dict[str, dict]:
    """Indexa todas las interacciones originales por ID."""

    lotes = (
        datos_fuente["lotes"]
        if "lotes" in datos_fuente
        else [datos_fuente]
    )

    indice: dict[str, dict] = {}

    for lote in lotes:
        origen = lote.get("origen_comunidad")
        periodo = lote.get("periodo_referencia")

        for mensaje in lote.get("interacciones", []):
            identificador = mensaje.get("id")

            if (
                not isinstance(identificador, str)
                or not identificador.strip()
            ):
                raise ValueError(
                    "La entrada contiene una interacción sin ID válido."
                )

            if identificador in indice:
                raise ValueError(
                    f"ID duplicado en la entrada: {identificador}"
                )

            indice[identificador] = {
                "id": identificador,
                "autor": mensaje.get("autor"),
                "canal": mensaje.get("canal"),
                "origen": origen,
                "periodo_referencia": periodo,
                "idioma": mensaje.get("idioma"),
                "texto": mensaje.get("texto"),
                "fecha": mensaje.get("fecha"),
                "tipo_original": mensaje.get("tipo"),
            }

    return indice


def _indexar_evaluaciones_data(
    paquete: dict,
) -> dict[str, dict]:
    """Indexa las decisiones de Data por ID."""

    informe = paquete.get("informe", {})
    indice: dict[str, dict] = {}

    for lote in informe.get("lotes", []):
        for evaluacion in lote.get("evaluaciones", []):
            identificador = evaluacion.get("id")

            if (
                not isinstance(identificador, str)
                or not identificador.strip()
            ):
                raise ValueError(
                    "El informe de Data contiene una evaluación "
                    "sin ID válido."
                )

            if identificador in indice:
                raise ValueError(
                    "El informe de Data contiene un ID duplicado: "
                    f"{identificador}"
                )

            indice[identificador] = deepcopy(evaluacion)

    return indice


def _indexar_resultados(
    salida_procesamiento: dict,
) -> dict[str, dict]:
    """Indexa la salida interna de DS por ID."""

    indice: dict[str, dict] = {}

    for resultado in salida_procesamiento.get(
        "resultados",
        [],
    ):
        identificador = resultado.get("id")

        if (
            not isinstance(identificador, str)
            or not identificador.strip()
        ):
            raise ValueError(
                "La salida de DS contiene un resultado sin ID válido."
            )

        if identificador in indice:
            raise ValueError(
                f"La salida de DS contiene un ID duplicado: {identificador}"
            )

        indice[identificador] = resultado

    return indice


def _modelo_para_evento(
    evento: dict,
    configuracion_ia: dict,
) -> str | None:
    """Resuelve el modelo efectivo a partir del proveedor y tier observados."""

    if evento.get("modelo"):
        return str(evento["modelo"])

    proveedor = evento.get("proveedor_usado")

    if proveedor == PROVEEDOR_GEMINI:
        return configuracion_ia.get("modelo_gemini")

    if proveedor == PROVEEDOR_NVIDIA_NIM:
        tier = evento.get("tier")
        modelos = configuracion_ia.get(
            "modelos_nvidia_por_tier",
            {},
        )
        return modelos.get(tier)

    return None


def _normalizar_traza(
    evento: dict,
    configuracion_ia: dict,
) -> dict:
    """Convierte un evento de observabilidad en evidencia auditable."""

    return {
        "tier": evento.get("tier"),
        "proveedor_primario": evento.get(
            "proveedor_primario"
        ),
        "proveedor_usado": evento.get(
            "proveedor_usado"
        ),
        "modelo": _modelo_para_evento(
            evento,
            configuracion_ia,
        ),
        "fallback_activado": bool(
            evento.get("fallback_activado", False)
        ),
        "motivo_fallback": evento.get(
            "motivo_fallback"
        ),
    }


def _indexar_trazas(
    eventos: list[dict],
    configuracion_ia: dict,
) -> tuple[
    dict[str, dict],
    dict[tuple[str, str], dict],
]:
    """Indexa trazas de análisis y generación.

    Si una interacción es reprocesada, el último evento de la misma
    ejecución prevalece.
    """

    trazas_analisis: dict[str, dict] = {}
    trazas_activos: dict[tuple[str, str], dict] = {}

    for evento in eventos:
        etapa = evento.get("etapa")
        traza = _normalizar_traza(
            evento,
            configuracion_ia,
        )

        if etapa in {
            "analizar_mensaje",
            "analizar_lote",
        }:
            identificador = evento.get(
                "id_interaccion"
            )

            if isinstance(identificador, str):
                trazas_analisis[identificador] = deepcopy(
                    traza
                )

            ids = evento.get("ids_interaccion")

            if isinstance(ids, list):
                for identificador_lote in ids:
                    if isinstance(
                        identificador_lote,
                        str,
                    ):
                        trazas_analisis[
                            identificador_lote
                        ] = deepcopy(traza)

            continue

        if etapa == "generar_activos":
            identificador = evento.get(
                "id_interaccion"
            )
            ruta = evento.get("ruta")

            if (
                isinstance(identificador, str)
                and isinstance(ruta, str)
            ):
                trazas_activos[
                    (identificador, ruta)
                ] = deepcopy(traza)

    return trazas_analisis, trazas_activos


def _construir_datos_interaccion(
    entrada: dict,
    evaluacion: dict,
) -> dict:
    """Construye la sección proveniente de Data."""

    motivos_exclusion = list(
        evaluacion.get(
            "motivos_exclusion_sentimiento",
            [],
        )
    )

    incluido_sentimiento = evaluacion.get(
        "incluido_sentimiento"
    )

    excluido_por_data = (
        incluido_sentimiento is False
        or bool(motivos_exclusion)
    )

    return {
        "tipo_original": entrada.get(
            "tipo_original"
        ),
        "score_relevancia": evaluacion.get(
            "puntaje"
        ),
        "elegible_contenido": bool(
            evaluacion.get("seleccionado", False)
        ),
        "elegible_faq": bool(
            evaluacion.get("elegible_faq", False)
        ),
        "motivos_data": list(
            evaluacion.get("motivos", [])
        ),
        "excluido_por_data": excluido_por_data,
        "motivos_exclusion": motivos_exclusion,
    }


def construir_paquete_auditoria(
    *,
    datos_fuente: dict,
    paquete_ia: dict,
    salida_procesamiento: dict,
    eventos_observabilidad: list[dict],
    configuracion_ia: dict,
    metadatos_ejecucion: dict,
) -> dict:
    """Construye el JSON de evidencia de Semana 4.

    No modifica ninguno de los objetos recibidos.
    """

    entradas = _indexar_entrada(
        datos_fuente
    )
    evaluaciones = _indexar_evaluaciones_data(
        paquete_ia
    )
    resultados = _indexar_resultados(
        salida_procesamiento
    )

    (
        trazas_analisis,
        trazas_activos,
    ) = _indexar_trazas(
        eventos_observabilidad,
        configuracion_ia,
    )

    ids_pendientes = set(
        salida_procesamiento.get(
            "ids_pendientes",
            [],
        )
    )

    entrega_estable = preparar_entrega_resultados(
        salida_procesamiento
    )

    resumen_comunidad = deepcopy(
        entrega_estable["resumen_comunidad"]
    )

    interacciones: list[dict] = []
    exclusiones_data: list[dict] = []
    inconsistencias: list[dict] = []

    total_activos = 0
    interacciones_con_fallback_analisis = 0
    activos_con_fallback = 0

    eventos_fallback_analisis = sum(
        1
        for evento in eventos_observabilidad
        if (
            evento.get("evento") == "proveedor_ia_resuelto"
            and evento.get("etapa")
            in {"analizar_mensaje", "analizar_lote"}
            and evento.get("fallback_activado") is True
        )
    )

    eventos_fallback_generacion = sum(
        1
        for evento in eventos_observabilidad
        if (
            evento.get("evento") == "proveedor_ia_resuelto"
            and evento.get("etapa") == "generar_activos"
            and evento.get("fallback_activado") is True
        )
    )

    for identificador, entrada in entradas.items():
        evaluacion = evaluaciones.get(
            identificador
        )

        if evaluacion is None:
            raise ValueError(
                "No existe evaluación de Data para "
                f"{identificador}."
            )

        datos = _construir_datos_interaccion(
            entrada,
            evaluacion,
        )

        resultado = resultados.get(
            identificador
        )

        registro = {
            "id": identificador,
            "entrada": {
                campo: deepcopy(valor)
                for campo, valor in entrada.items()
                if campo not in {
                    "id",
                    "tipo_original",
                }
            },
            "datos": datos,
            "pendiente_procesamiento": (
                identificador in ids_pendientes
            ),
            "analisis": None,
            "rutas": [],
            "activos": {},
            "errores": [],
            "fallos": [],
        }

        if datos["excluido_por_data"]:
            exclusiones_data.append(
                {
                    "id": identificador,
                    "motivos": deepcopy(
                        datos["motivos_exclusion"]
                    ),
                }
            )

            if resultado is not None:
                inconsistencias.append(
                    {
                        "id": identificador,
                        "tipo": (
                            "excluido_data_con_resultado_ds"
                        ),
                    }
                )

            interacciones.append(registro)
            continue

        if resultado is None:
            if identificador not in ids_pendientes:
                inconsistencias.append(
                    {
                        "id": identificador,
                        "tipo": (
                            "incluido_data_sin_resultado_ds"
                        ),
                    }
                )

            interacciones.append(registro)
            continue

        registro["rutas"] = deepcopy(
            resultado.get("rutas", [])
        )
        registro["errores"] = deepcopy(
            resultado.get("errores", [])
        )
        registro["fallos"] = deepcopy(
            resultado.get("fallos", [])
        )

        campos_analisis = (
            "sentimiento",
            "tema_principal",
            "subtema",
            "tipo_detectado",
        )

        if all(
            campo in resultado
            for campo in campos_analisis
        ):
            traza_analisis = trazas_analisis.get(
                identificador
            )

            registro["analisis"] = {
                campo: deepcopy(resultado.get(campo))
                for campo in campos_analisis
            }

            # Conservar la señal de spam en la auditoría.
            for campo in ("es_spam_detectado", "motivo_spam"):
                if campo in resultado:
                    registro["analisis"][campo] = deepcopy(
                        resultado[campo]
                    )

            registro["analisis"]["trazabilidad"] = deepcopy(
                traza_analisis
            )

            if traza_analisis is None:
                inconsistencias.append(
                    {
                        "id": identificador,
                        "tipo": (
                            "analisis_sin_trazabilidad"
                        ),
                    }
                )
            elif traza_analisis.get(
                "fallback_activado"
            ):
                interacciones_con_fallback_analisis += 1

        for ruta, contenido in resultado.get(
            "activos_generados",
            {},
        ).items():
            traza = trazas_activos.get(
                (identificador, ruta)
            )

            registro["activos"][ruta] = {
                "contenido": deepcopy(contenido),
                "trazabilidad": deepcopy(traza),
            }

            total_activos += 1

            if traza is None:
                inconsistencias.append(
                    {
                        "id": identificador,
                        "ruta": ruta,
                        "tipo": (
                            "activo_sin_trazabilidad"
                        ),
                    }
                )
            elif traza.get(
                "fallback_activado"
            ):
                activos_con_fallback += 1

        interacciones.append(registro)

    return {
        "version_auditoria": VERSION_AUDITORIA_SEMANA4,
        "ejecucion": {
            **deepcopy(metadatos_ejecucion),
            "id_ejecucion": salida_procesamiento.get(
                "id_ejecucion"
            ),
            "configuracion_ia": deepcopy(
                configuracion_ia
            ),
        },
        "resumen": {
            "total_entrada": len(entradas),
            "total_excluidas_data": len(
                exclusiones_data
            ),
            "total_resultados_ds": len(
                resultados
            ),
            **resumen_comunidad,
            "interacciones_con_fallback_analisis": (
                interacciones_con_fallback_analisis
            ),
            "eventos_fallback_analisis": (
                eventos_fallback_analisis
            ),
            "activos_con_fallback": (
                activos_con_fallback
            ),
            "eventos_fallback_generacion": (
                eventos_fallback_generacion
            ),
            "total_inconsistencias": len(
                inconsistencias
            ),
        },
        "exclusiones_data": exclusiones_data,
        "interacciones": interacciones,
        "inconsistencias": inconsistencias,
    }


def paquete_auditoria_a_json(
    paquete: dict,
    *,
    indentacion: int = 2,
) -> str:
    """Serializa el paquete de auditoría en UTF-8 lógico."""

    return json.dumps(
        paquete,
        ensure_ascii=False,
        indent=indentacion,
    )
