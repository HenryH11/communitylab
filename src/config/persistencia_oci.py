"""Borrador del conector de JSON a OCI Object Storage (Semana 2).

La integración con el cierre del workflow se realizará en Semana 3. Este módulo
no imprime credenciales ni escribe archivos locales.
"""

import json
import os
import re
from collections.abc import Mapping
from typing import Any

import oci


BUCKET_PREDETERMINADO = "communitylab-activos-marketing"
RUTAS_ACTIVO = frozenset({"linkedin", "boletin", "preguntas_frecuentes", "caso_exito"})
_SEGMENTO = re.compile(r"[A-Za-z0-9_-]+\Z")


def nombre_objeto_activo(identificador: str, ruta: str, periodo: str) -> str:
    """Construye una clave estable, sin separadores aportados por la entrada."""
    for nombre, valor in (("id", identificador), ("periodo", periodo)):
        if not isinstance(valor, str) or not _SEGMENTO.fullmatch(valor):
            raise ValueError(f"{nombre} debe contener solo letras, números, _ o -")
    if ruta not in RUTAS_ACTIVO:
        raise ValueError("ruta de activo no admitida")
    return f"assets/{periodo}/{ruta}/{identificador}.json"


def crear_cliente(perfil: str | None = None) -> tuple[Any, str]:
    """Carga un perfil OCI local y obtiene el namespace de Object Storage."""
    configuracion = oci.config.from_file(profile_name=perfil or os.getenv("OCI_PROFILE", "DEFAULT"))
    oci.config.validate_config(configuracion)
    cliente = oci.object_storage.ObjectStorageClient(configuracion)
    namespace = cliente.get_namespace().data
    return cliente, namespace


def subir_json(
    documento: Mapping[str, Any],
    nombre_objeto: str,
    *,
    cliente: Any | None = None,
    namespace: str | None = None,
    bucket: str | None = None,
    perfil: str | None = None,
) -> dict[str, str | None]:
    """Serializa y sube un documento; devuelve ubicación y ETag de OCI.

    Para pruebas se inyectan ``cliente`` y ``namespace``. En uso real se leen
    las credenciales del perfil local. Los errores del SDK se propagan al
    llamador, que decidirá cómo mostrarlos o reintentarlos.
    """
    if not isinstance(documento, Mapping):
        raise TypeError("documento debe ser un diccionario JSON")
    if not isinstance(nombre_objeto, str) or not nombre_objeto.strip() or nombre_objeto.startswith("/"):
        raise ValueError("nombre_objeto debe ser una ruta relativa no vacía")
    if cliente is None:
        cliente, namespace = crear_cliente(perfil)
    elif not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("namespace es obligatorio al inyectar un cliente")

    bucket_efectivo = bucket or os.getenv("OCI_BUCKET_NAME", BUCKET_PREDETERMINADO)
    if not isinstance(bucket_efectivo, str) or not bucket_efectivo.strip():
        raise ValueError("bucket debe ser un nombre no vacío")

    cuerpo = json.dumps(documento, ensure_ascii=False, allow_nan=False).encode("utf-8")
    respuesta = cliente.put_object(
        namespace_name=namespace,
        bucket_name=bucket_efectivo,
        object_name=nombre_objeto,
        put_object_body=cuerpo,
        content_type="application/json; charset=utf-8",
    )
    return {
        "bucket": bucket_efectivo,
        "namespace": namespace,
        "object_name": nombre_objeto,
        "etag": respuesta.headers.get("etag") if respuesta.headers else None,
    }
