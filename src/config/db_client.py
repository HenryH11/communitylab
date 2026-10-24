"""Cliente de solo lectura para consultas en Oracle Autonomous Database.

Gestiona la conexión TLS Thin hacia la base de datos INSUMOS para la
recuperación del Conjunto Consultable. Para la autenticación en OCI IAM
se obtienen credenciales desde OCI Vault y se realiza mediante Instance
Principals.
"""

import base64
from functools import lru_cache
import os
import re
from typing import Any

from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
from oci.secrets import SecretsClient
import oracledb

# Forzar al driver a devolver CLOBs como str y BLOBs como bytes
oracledb.defaults.fetch_lobs = False

USUARIO_PREDETERMINADO = "ro_query_communitylab"
VERSION_CONJUNTO = "1.1"
CAMPOS_CONJUNTO = (
    "id",
    "canal",
    "sentimiento",
    "tema",
    "tipo",
    "contenido_textual",
    "fecha",
)
_SEGMENTO = re.compile(r"[A-Za-z0-9_-]+\Z")

_SQL_SELECT_TODOS = """
SELECT
    m.version, m.total, m.total_spam_excluido,
    d.id, d.canal, d.sentimiento, d.tema, d.tipo, d.contenido_textual,
    CASE
        WHEN d.fecha IS NOT NULL THEN
            TO_CHAR(d.fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        ELSE NULL
    END AS fecha
FROM rw_ingest_communitylab.conjunto_consultable_meta m
LEFT JOIN rw_ingest_communitylab.conjunto_consultable d ON 1 = 1
WHERE m.id = 1
ORDER BY d.id ASC
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
    secreto = base64.b64decode(contenido_b64, validate=True).decode("utf-8")
    if not secreto:
        raise ValueError("el secreto está vacío")
    return secreto


@lru_cache(maxsize=4)
def _obtener_secreto_cache(ocid_secreto: str) -> str:
    """Resuelve y mantiene en caché el secreto usando el cliente base."""
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
    ocid_efectivo = ocid_secreto or os.getenv("DB_READ_PASSWORD_SECRET_OCID")
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
        usuario or os.getenv("DB_READ_USER") or USUARIO_PREDETERMINADO
    )
    if not isinstance(usuario_efectivo, str) or not _SEGMENTO.fullmatch(
        usuario_efectivo.strip()
    ):
        raise ValueError("usuario debe contener solo letras, números, _ o -")

    dsn_efectivo = dsn or os.getenv("DB_READ_DSN") or os.getenv("DB_DSN")
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


def obtener_conexion_lectura() -> oracledb.Connection:
    """Exige credenciales de lectura; permisos SELECT configurados en OCI."""
    usuario = os.getenv("DB_READ_USER", "").strip()
    secreto = os.getenv("DB_READ_PASSWORD_SECRET_OCID", "").strip()
    escritor = os.getenv("DB_USER", "").strip()
    if not usuario or not secreto:
        raise ValueError(
            "configura DB_READ_USER y DB_READ_PASSWORD_SECRET_OCID"
        )
    usuarios_escritores = {"RW_INGEST_COMMUNITYLAB", "AGENT_COMMUNITYLAB"}
    if escritor:
        usuarios_escritores.add(escritor.upper())
    if usuario.upper() in usuarios_escritores:
        raise ValueError(
            "configura un DB_READ_USER distinto al usuario de escritura"
        )
    return obtener_conexion(
        usuario=usuario,
        dsn=os.getenv("DB_READ_DSN") or os.getenv("DB_DSN"),
        ocid_secreto=secreto,
    )


def leer_conjunto(
    *,
    conexion: oracledb.Connection | None = None,
) -> dict[str, Any]:
    """Lee filas y metadatos en una sola consulta consistente y sin commit.

    Para el agente, inyectar una conexión de solo SELECT, con acceso a
    ambas tablas. No conectar el agente público con el usuario cargador.
    """
    if conexion is not None:
        with conexion.cursor() as cursor:
            cursor.execute(_SQL_SELECT_TODOS)
            filas = cursor.fetchall()
    else:
        with (
            obtener_conexion_lectura() as conexion_activa,
            conexion_activa.cursor() as cursor,
        ):
            cursor.execute(_SQL_SELECT_TODOS)
            filas = cursor.fetchall()

    if not filas:
        raise ValueError("no hay una instantánea publicada con metadatos")
    version, total, spam = filas[0][:3]
    registros = [
        dict(zip(CAMPOS_CONJUNTO, fila[3:]))
        for fila in filas
        if fila[3] is not None
    ]
    if total != len(registros):
        raise ValueError(
            "la tabla no coincide con el total de la instantánea publicada"
        )
    return {
        "version": version,
        "campos": list(CAMPOS_CONJUNTO),
        "total": total,
        **(
            {"total_spam_excluido": spam}
            if version == VERSION_CONJUNTO
            else {}
        ),
        "registros": registros,
    }
