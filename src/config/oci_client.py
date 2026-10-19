"""Cliente para persistencia de datos en OCI.

Gestiona la subida de activos de Marketing (objetos) en formato JSON
hacia OCI Object Storage. La autenticación en OCI IAM se realiza a
través de Instance Principals. Este módulo expone funciones silenciosas
al orquestador del workflow.
"""

import json
import os
import re
from functools import lru_cache
from collections.abc import Mapping
from typing import Any

from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
from oci.object_storage import ObjectStorageClient


BUCKET_PREDETERMINADO = "bkt-communitylab-marketing"
RUTAS_ACTIVO = frozenset({
    "linkedin",
    "boletin",
    "preguntas_frecuentes",
    "caso_exito",
    "insight_mejora",
})
_SEGMENTO = re.compile(r"[A-Za-z0-9_-]+\Z")


def nombre_objeto_activo(identificador: str, ruta: str, periodo: str) -> str:
    """Construye una clave segura y sanitizada para el activo."""
    for nombre, valor in (("id", identificador), ("periodo", periodo)):
        if not isinstance(valor, str) or not _SEGMENTO.fullmatch(valor):
            raise ValueError(
                f"{nombre} debe contener solo letras, números, _ o -"
            )
    if ruta not in RUTAS_ACTIVO:
        raise ValueError("ruta de activo no admitida")
    return f"activos/{periodo}/{ruta}/{identificador}.json"


@lru_cache(maxsize=1)
def obtener_cliente() -> tuple[ObjectStorageClient, str]:
    """Inicializa y almacena en caché el cliente y el namespace de OCI.

    Consulta el servicio IMDSv2 para obtener el firmante mediante
    Instance Principals y resuelve el namespace de forma dinámica. La
    caché en memoria garantiza que la negociación se ejecute por única
    vez para cada ejecución del programa.
    """
    signer = InstancePrincipalsSecurityTokenSigner()
    cliente = ObjectStorageClient(config={}, signer=signer)
    namespace = cliente.get_namespace().data
    return cliente, namespace


def subir_json(
    documento: Mapping[str, Any],
    nombre_objeto: str,
    *,
    cliente: ObjectStorageClient | None = None,
    namespace: str | None = None,
    bucket: str | None = None,
) -> dict[str, str | None]:
    """Serializa y sube un documento; devuelve ubicación y ETag de OCI.

    Reutiliza por defecto la instancia de cliente y namespace en memoria
    gestionada por ``obtener_cliente()``. Permite inyectar ``cliente`` y
    ``namespace`` para pruebas unitarias o aislamiento de dependencias.
    Los errores del SDK se propagan al llamador, el cual decidirá cómo
    mostrarlos o reintentarlos.
    """
    if not isinstance(documento, Mapping):
        raise TypeError("documento debe ser un diccionario JSON")
    if (
        not isinstance(nombre_objeto, str)
        or not nombre_objeto.strip()
        or nombre_objeto.startswith("/")
    ):
        raise ValueError("nombre_objeto debe ser una ruta relativa no vacía")
    if cliente is None:
        cliente, namespace = obtener_cliente()
    elif not isinstance(namespace, str) or not namespace.strip():
        raise ValueError("namespace es obligatorio al inyectar un cliente")

    bucket_efectivo = (
        bucket
        or os.getenv("OCI_BUCKET_NAME", BUCKET_PREDETERMINADO)
    )
    if not isinstance(bucket_efectivo, str) or not bucket_efectivo.strip():
        raise ValueError("bucket debe ser un nombre no vacío")

    cuerpo = json.dumps(
        documento,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
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