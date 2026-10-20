"""Cliente para persistencia y consultas en Oracle Autonomous Database.

Gestiona la conexión TLS Thin hacia la base de datos INSUMOS y la
sincronización del Conjunto Consultable. La autenticación en OCI IAM
para recuperar credenciales desde OCI Vault se realiza a través de
Instance Principals. Este módulo expone funciones silenciosas al
orquestador del workflow.
"""

import re
from functools import lru_cache
import base64
import os
from collections.abc import Mapping, Sequence
from typing import Any

from oci.secrets import SecretsClient
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
import oracledb


USUARIO_PREDETERMINADO = "agent_communitylab"
TABLA_PREDETERMINADA = "conjunto_consultable"
VERSION_CONJUNTO = "1.0"
CAMPOS_CONJUNTO = (
    "id",
    "canal",
    "sentimiento",
    "tema",
    "tipo",
    "contenido_corto",
    "fecha",
)
_CAMPOS_REQUERIDOS = frozenset(CAMPOS_CONJUNTO)
_SEGMENTO = re.compile(r"[A-Za-z0-9_-]+\Z")

_SQL_UPSERT = """
MERGE INTO conjunto_consultable destino
USING (
    SELECT
        :id AS id,
        :canal AS canal,
        :sentimiento AS sentimiento,
        :tema AS tema,
        :tipo AS tipo,
        :contenido_corto AS contenido_corto,
        CASE
            WHEN :fecha IS NOT NULL THEN
                TO_TIMESTAMP_TZ(:fecha, 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
            ELSE NULL
        END AS fecha
    FROM dual
) origen
ON (destino.id = origen.id)
WHEN MATCHED THEN
    UPDATE SET
        destino.canal = origen.canal,
        destino.sentimiento = origen.sentimiento,
        destino.tema = origen.tema,
        destino.tipo = origen.tipo,
        destino.contenido_corto = origen.contenido_corto,
        destino.fecha = origen.fecha
WHEN NOT MATCHED THEN
    INSERT (
        id, canal, sentimiento, tema, tipo, contenido_corto, fecha
    )
    VALUES (
        origen.id,
        origen.canal,
        origen.sentimiento,
        origen.tema,
        origen.tipo,
        origen.contenido_corto,
        origen.fecha
    )
"""

_SQL_SELECT_TODOS = """
SELECT
    id,
    canal,
    sentimiento,
    tema,
    tipo,
    contenido_corto,
    CASE
        WHEN fecha IS NOT NULL THEN
            TO_CHAR(fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        ELSE NULL
    END AS fecha
FROM conjunto_consultable
ORDER BY id ASC
"""


@lru_cache(maxsize=1)
def obtener_cliente_secretos() -> SecretsClient:
    """Inicializa y almacena en caché el cliente de secretos de OCI.

    Consulta el servicio IMDSv2 para obtener el firmante mediante
    Instance Principals. La caché en memoria garantiza que la
    negociación se realice una única vez por ejecución del programa.
    """
    signer = InstancePrincipalsSecurityTokenSigner()
    return SecretsClient(config={}, signer=signer)


def _descargar_secreto(cliente: SecretsClient, ocid_secreto: str) -> str:
    """Extrae y decodifica el contenido Base64 de un secreto en OCI Vault."""
    respuesta = cliente.get_secret_bundle(secret_id=ocid_secreto)
    contenido_b64 = respuesta.data.secret_bundle_content.content
    return base64.b64decode(contenido_b64).decode("utf-8").strip()


@lru_cache(maxsize=4)
def _obtener_secreto_cache(ocid_secreto: str) -> str:
    """Resuelve y mantiene en caché el secreto usando el cliente por defecto."""
    cliente = obtener_cliente_secretos()
    return _descargar_secreto(cliente, ocid_secreto)


def obtener_secreto_vault(
    ocid_secreto: str | None = None,
    *,
    cliente: SecretsClient | None = None,
) -> str:
    """Recupera un secreto en texto plano desde OCI Vault.

    Reutiliza por defecto la instancia en memoria de ``SecretsClient``.
    Permite inyectar ``cliente`` para pruebas unitarias o aislamiento
    de dependencias sin tocar la caché global.
    """
    ocid_efectivo = ocid_secreto or os.getenv("DB_PASSWORD_SECRET_OCID")
    if not isinstance(ocid_efectivo, str) or not ocid_efectivo.strip():
        raise ValueError("ocid_secreto debe ser una cadena no vacía")

    ocid_limpio = ocid_efectivo.strip()
    if cliente is not None:
        return _descargar_secreto(cliente, ocid_limpio)
    return _obtener_secreto_cache(ocid_limpio)


def obtener_conexion(
    *,
    usuario: str | None = None,
    dsn: str | None = None,
    ocid_secreto: str | None = None,
    cliente_secretos: SecretsClient | None = None,
) -> oracledb.Connection:
    """Establece una conexión TLS Thin hacia la base de datos."""
    usuario_efectivo = (
        usuario
        or os.getenv("DB_USER", USUARIO_PREDETERMINADO)
    )
    if not isinstance(usuario_efectivo, str) or not _SEGMENTO.fullmatch(
        usuario_efectivo.strip()
    ):
        raise ValueError(
            "usuario debe contener solo letras, números, _ o -"
        )

    dsn_efectivo = dsn or os.getenv("DB_DSN")
    if not isinstance(dsn_efectivo, str) or not dsn_efectivo.strip():
        raise ValueError("dsn debe ser una cadena de conexión no vacía")

    contrasena = obtener_secreto_vault(
        ocid_secreto,
        cliente=cliente_secretos,
    )
    return oracledb.connect(
        user=usuario_efectivo.strip(),
        password=contrasena,
        dsn=dsn_efectivo.strip(),
    )


def validar_registro(registro: Mapping[str, Any]) -> dict[str, Any]:
    """Valida los 7 campos y sanitiza el identificador de un registro."""
    if not isinstance(registro, Mapping):
        raise TypeError("cada registro debe ser un diccionario JSON")
    if not _CAMPOS_REQUERIDOS.issubset(registro.keys()):
        raise ValueError("el registro no contiene los 7 campos requeridos")

    identificador = registro.get("id")
    if not isinstance(identificador, str) or not _SEGMENTO.fullmatch(
        identificador
    ):
        raise ValueError(
            "id debe contener solo letras, números, _ o -"
        )
    return {campo: registro[campo] for campo in CAMPOS_CONJUNTO}


def _preparar_lote(
    documento: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Extrae la lista de registros y verifica que no existan duplicados."""
    if not isinstance(documento, Mapping):
        raise TypeError("documento debe ser un diccionario JSON")

    registros = documento.get("registros")
    if not isinstance(registros, Sequence) or isinstance(
        registros, (str, bytes)
    ):
        raise ValueError("documento debe contener una lista en 'registros'")

    lote = [validar_registro(item) for item in registros]
    ids = [item["id"] for item in lote]
    if len(ids) != len(set(ids)):
        raise ValueError("se detectaron identificadores duplicados")
    return lote


def sincronizar_conjunto(
    documento: Mapping[str, Any],
    *,
    conexion: oracledb.Connection | None = None,
) -> dict[str, str | int]:
    """Ejecuta un upsert (MERGE) del Conjunto Consultable en la BD.

    Permite inyectar ``conexion`` para pruebas unitarias. Si no se
    provee, gestiona el ciclo de vida de una conexión obtenida mediante
    ``obtener_conexion()``.
    """
    lote = _preparar_lote(documento)
    if not lote:
        return {"tabla": TABLA_PREDETERMINADA, "sincronizados": 0}

    if conexion is not None:
        with conexion.cursor() as cursor:
            cursor.executemany(_SQL_UPSERT, lote)
        conexion.commit()
        return {"tabla": TABLA_PREDETERMINADA, "sincronizados": len(lote)}

    with (
        obtener_conexion() as conexion_activa,
        conexion_activa.cursor() as cursor,
    ):
        cursor.executemany(_SQL_UPSERT, lote)
        conexion_activa.commit()

    return {"tabla": TABLA_PREDETERMINADA, "sincronizados": len(lote)}


def leer_conjunto(
    *,
    conexion: oracledb.Connection | None = None,
) -> dict[str, Any]:
    """Reconstruye el diccionario del Conjunto Consultable desde la BD."""
    if conexion is not None:
        with conexion.cursor() as cursor:
            cursor.execute(_SQL_SELECT_TODOS)
            columnas = [col[0].lower() for col in cursor.description]
            filas = cursor.fetchall()
    else:
        with (
            obtener_conexion() as conexion_activa,
            conexion_activa.cursor() as cursor,
        ):
            cursor.execute(_SQL_SELECT_TODOS)
            columnas = [col[0].lower() for col in cursor.description]
            filas = cursor.fetchall()

    registros = [dict(zip(columnas, fila)) for fila in filas]
    return {
        "version": VERSION_CONJUNTO,
        "campos": list(CAMPOS_CONJUNTO),
        "total": len(registros),
        "registros": registros,
    }