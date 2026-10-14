"""Guardado posterior al grafo, limitado a los activos aprobados por la UI.

La selección pertenece a la capa de aplicación, no al contrato JSON de DS.
Importar este módulo o pasar una selección vacía no requiere el SDK de OCI.
"""

import asyncio
import json
from collections.abc import Collection
from typing import Any

from src.agentes.entrega_resultados import preparar_entrega_resultados

ClaveActivo = tuple[str, str]


def _identidad(activo: dict) -> dict[str, str]:
    return {
        "id_interaccion": activo["id_interaccion"],
        "tipo": activo["tipo"],
    }


def _guardar_seleccion(
    activos: list[dict],
    *,
    periodo: str,
    bucket: str,
    cliente: Any,
    namespace: str | None,
) -> dict[str, list[dict]]:
    # Carga diferida: consultar resultados sin guardar no exige el SDK.
    from src.config.oci_client import nombre_objeto_activo, subir_json

    if cliente is not None and (
        not isinstance(namespace, str) or not namespace.strip()
    ):
        raise ValueError("namespace es obligatorio al inyectar un cliente")

    trabajos = []
    for activo in activos:
        nombre = nombre_objeto_activo(
            activo["id_interaccion"], activo["tipo"], periodo
        )
        if not isinstance(activo["contenido"], dict):
            raise ValueError(
                "El contenido de cada activo debe ser un diccionario"
            )
        # Validar TODO el lote aprobado antes de la primera escritura.
        json.dumps(activo, ensure_ascii=False, allow_nan=False).encode("utf-8")
        trabajos.append((activo, nombre))

    informe: dict[str, list[dict]] = {"guardados": [], "fallidos": []}
    for activo, nombre in trabajos:
        identidad = _identidad(activo)
        try:
            ubicacion = subir_json(
                activo,
                nombre,
                cliente=cliente,
                namespace=namespace,
                bucket=bucket,
            )
        except Exception as error:
            # No exponer mensajes del SDK ni credenciales a la UI.
            estado_http = getattr(error, "status", None)
            informe["fallidos"].append(
                {
                    **identidad,
                    "object_name": nombre,
                    "tipo_error": type(error).__name__,
                    "estado_http": (
                        estado_http if type(estado_http) is int else None
                    ),
                    "mensaje": "No se pudo confirmar el guardado en OCI.",
                }
            )
        else:
            informe["guardados"].append({**identidad, **ubicacion})
    return informe


async def guardar_resultado_aprobado(
    salida_procesamiento: dict,
    *,
    aprobados: Collection[ClaveActivo],
    periodo: str,
    bucket: str,
    cliente: Any | None = None,
    namespace: str | None = None,
) -> dict[str, list[dict]]:
    """Guarda una selección de la salida final de ``procesar_paquete_entrega``.

    ``aprobados`` contiene pares (id_interaccion, tipo) elegidos después de
    revisar esa misma salida. Una selección vacía no realiza llamadas a OCI.
    El bucket explícito evita depender de un nombre predeterminado antiguo.

    Devuelve un informe separado: ``guardados``, ``fallidos`` y ``omitidos``;
    no modifica la salida ni el contrato de DS. Los errores de validación se
    propagan antes de subir cualquier activo. Los errores durante la subida
    se registran por activo y no se confirman como guardados.

    El SDK síncrono trabaja secuencialmente en un hilo, sin bloquear el bucle
    asíncrono ni compartir un cliente entre subidas paralelas de este lote.
    """
    if (
        not isinstance(bucket, str)
        or not bucket.strip()
        or bucket != bucket.strip()
    ):
        raise ValueError("bucket debe ser un nombre explícito no vacío")
    if not isinstance(aprobados, (list, tuple, set, frozenset)):
        raise ValueError(
            "aprobados debe contener pares (id_interaccion, tipo)"
        )

    seleccion = set()
    for clave in aprobados:
        if (
            not isinstance(clave, tuple)
            or len(clave) != 2
            or not all(isinstance(valor, str) and valor for valor in clave)
        ):
            raise ValueError(
                "Cada aprobación debe ser un par (id_interaccion, tipo)"
            )
        seleccion.add(clave)

    # DS valida la salida y copia el contenido: nunca se modifica el original.
    entrega = preparar_entrega_resultados(salida_procesamiento)
    activos = entrega["activos"]
    disponibles = {(a["id_interaccion"], a["tipo"]) for a in activos}
    if not seleccion.issubset(disponibles):
        raise ValueError(
            "Hay aprobaciones que no corresponden a activos de esta salida"
        )

    elegidos = []
    omitidos = []
    for activo in activos:
        if (activo["id_interaccion"], activo["tipo"]) in seleccion:
            elegidos.append(activo)
        else:
            omitidos.append(_identidad(activo))

    if not elegidos:
        return {"guardados": [], "fallidos": [], "omitidos": omitidos}

    informe = await asyncio.to_thread(
        _guardar_seleccion,
        elegidos,
        periodo=periodo,
        bucket=bucket,
        cliente=cliente,
        namespace=namespace,
    )
    return {**informe, "omitidos": omitidos}
