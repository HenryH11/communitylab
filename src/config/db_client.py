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
from datetime import datetime
from collections.abc import Mapping, Sequence
from typing import Any

from oci.secrets import SecretsClient
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
import oracledb

USUARIO_PREDETERMINADO = "agent_communitylab"
TABLA_PREDETERMINADA = "conjunto_consultable"
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
        :contenido_textual AS contenido_textual,
        CASE
            WHEN :fecha IS NOT NULL THEN
                TO_TIMESTAMP_TZ(
                    REPLACE(:fecha, 'Z', '+00:00'),
                    'YYYY-MM-DD"T"HH24:MI:SSTZH:TZM'
                )
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
        destino.contenido_textual = origen.contenido_textual,
        destino.fecha = origen.fecha
WHEN NOT MATCHED THEN
    INSERT (
        id, canal, sentimiento, tema, tipo, contenido_textual, fecha
    )
    VALUES (
        origen.id,
        origen.canal,
        origen.sentimiento,
        origen.tema,
        origen.tipo,
        origen.contenido_textual,
        origen.fecha
    )
"""

_SQL_META = """
MERGE INTO conjunto_consultable_meta destino
USING (SELECT 1 AS id, :version AS version, :total AS total,
              :total_spam_excluido AS total_spam_excluido FROM dual) origen
ON (destino.id = origen.id)
WHEN MATCHED THEN UPDATE SET
    destino.version = origen.version, destino.total = origen.total,
    destino.total_spam_excluido = origen.total_spam_excluido
WHEN NOT MATCHED THEN INSERT (id, version, total, total_spam_excluido)
VALUES (origen.id, origen.version, origen.total, origen.total_spam_excluido)
"""

_SQL_SELECT_TODOS = """
SELECT
    m.version, m.total, m.total_spam_excluido,
    d.id, d.canal, d.sentimiento, d.tema, d.tipo, d.contenido_textual,
    CASE
        WHEN d.fecha IS NOT NULL THEN
            TO_CHAR(d.fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        ELSE NULL
    END AS fecha
FROM conjunto_consultable_meta m
LEFT JOIN conjunto_consultable d ON 1 = 1
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
    if respuesta is None:
        raise RuntimeError("OCI Vault no devolvió el secreto solicitado")
    contenido_b64 = respuesta.data.secret_bundle_content.content
    secreto = base64.b64decode(contenido_b64, validate=True).decode("utf-8")
    if not secreto:
        raise ValueError("el secreto está vacío")
    return secreto


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
    usuario_efectivo = usuario or os.getenv("DB_USER", USUARIO_PREDETERMINADO)
    if not isinstance(usuario_efectivo, str) or not _SEGMENTO.fullmatch(
        usuario_efectivo.strip()
    ):
        raise ValueError("usuario debe contener solo letras, números, _ o -")

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
    if set(registro) != _CAMPOS_REQUERIDOS:
        raise ValueError("el registro no contiene los 7 campos requeridos")

    identificador = registro.get("id")
    if not isinstance(identificador, str) or not _SEGMENTO.fullmatch(
        identificador
    ):
        raise ValueError("id debe contener solo letras, números, _ o -")
    # La tabla de INSUMOS exige NOT NULL para estas cuatro columnas.
    # Solo comprobar strip(): no modificar el texto que entrega DA.
    for campo in ("canal", "sentimiento", "tema", "tipo"):
        valor = registro[campo]
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{campo} debe ser texto no vacío, no null")
    contenido = registro["contenido_textual"]
    if not isinstance(contenido, str) or not contenido.strip():
        raise ValueError(
            "contenido_textual debe ser texto no vacío"
        )
    for valor in registro.values():
        if isinstance(valor, str):
            valor.encode("utf-8")
    fecha = registro["fecha"]
    if fecha is not None:
        if not isinstance(fecha, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", fecha
        ):
            raise ValueError(
                "fecha debe ser UTC con formato YYYY-MM-DDTHH:MM:SSZ o null"
            )
        datetime.strptime(fecha, "%Y-%m-%dT%H:%M:%SZ")
    return {campo: registro[campo] for campo in CAMPOS_CONJUNTO}


def obtener_conexion_lectura() -> oracledb.Connection:
    """Exige credenciales separadas; los permisos SELECT se configuran en OCI."""
    usuario = os.getenv("DB_READ_USER", "").strip()
    secreto = os.getenv("DB_READ_PASSWORD_SECRET_OCID", "").strip()
    escritor = os.getenv("DB_USER", USUARIO_PREDETERMINADO).strip()
    if not usuario or not secreto or usuario.upper() == escritor.upper():
        raise ValueError(
            "configura un DB_READ_USER distinto y su DB_READ_PASSWORD_SECRET_OCID"
        )
    return obtener_conexion(
        usuario=usuario,
        dsn=os.getenv("DB_READ_DSN") or os.getenv("DB_DSN"),
        ocid_secreto=secreto,
    )


def _preparar_lote(
    documento: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Extrae la lista de registros y verifica que no existan duplicados."""
    if not isinstance(documento, Mapping):
        raise TypeError("documento debe ser un diccionario JSON")

    if documento.get("version") not in ("1.0", VERSION_CONJUNTO):
        raise ValueError("versión del Conjunto Consultable no admitida")
    if documento.get("campos") != list(CAMPOS_CONJUNTO):
        raise ValueError("campos no coincide con el contrato de DA")

    registros = documento.get("registros")
    if not isinstance(registros, Sequence) or isinstance(
        registros, (str, bytes)
    ):
        raise ValueError("documento debe contener una lista en 'registros'")

    lote = [validar_registro(item) for item in registros]
    total = documento.get("total")
    if type(total) is not int or total != len(lote):
        raise ValueError("total no coincide con la cantidad de registros")
    spam = documento.get("total_spam_excluido", 0)
    if (
        type(spam) is not int
        or spam < 0
        or (
            documento["version"] == VERSION_CONJUNTO
            and "total_spam_excluido" not in documento
        )
        or (documento["version"] == "1.0" and spam != 0)
    ):
        raise ValueError("total_spam_excluido no es válido para esta versión")
    ids = [item["id"] for item in lote]
    if len(ids) != len(set(ids)):
        raise ValueError("se detectaron identificadores duplicados")
    return lote


def sincronizar_conjunto(
    documento: Mapping[str, Any],
    *,
    conexion: oracledb.Connection | None = None,
    instantanea_completa: bool = False,
) -> dict[str, str | int]:
    """Publica una instantánea completa; no admite cargas incrementales.

    Permite inyectar ``conexion`` para pruebas unitarias. Si no se
    provee, gestiona el ciclo de vida de una conexión obtenida mediante
    ``obtener_conexion()``. La conexión debe ser exclusiva, sin trabajo
    pendiente y con autocommit desactivado. Requiere la tabla de metadatos.
    Se retiran los IDs ausentes SOLO con instantanea_completa=True, incluso
    si la instantánea está vacía. No usar con tablas compartidas entre datasets.
    """
    lote = _preparar_lote(documento)
    if instantanea_completa is not True:
        raise ValueError(
            "confirma instantanea_completa=True; no se admiten lotes parciales"
        )

    if conexion is not None:
        retirados = _publicar_instantanea(conexion, documento, lote)
    else:
        with obtener_conexion() as conexion_activa:
            retirados = _publicar_instantanea(conexion_activa, documento, lote)

    return {
        "tabla": TABLA_PREDETERMINADA,
        "sincronizados": len(lote),
        "retirados": retirados,
    }


def _publicar_instantanea(conexion, documento, lote):
    if conexion.autocommit or conexion.transaction_in_progress:
        raise ValueError(
            "usa una conexión exclusiva sin transacción activa y sin autocommit"
        )
    try:
        with conexion.cursor() as cursor:
            # Serializa cargadores sin bloquear lecturas; evita espera indefinida.
            cursor.execute(
                "LOCK TABLE conjunto_consultable, conjunto_consultable_meta "
                "IN EXCLUSIVE MODE NOWAIT"
            )
            cursor.execute("SELECT id FROM conjunto_consultable")
            ids_actuales = {fila[0] for fila in cursor.fetchall()}
            ids_nuevos = {fila["id"] for fila in lote}
            retirados = sorted(ids_actuales - ids_nuevos)
            if lote:
                cursor.setinputsizes(contenido_textual=oracledb.DB_TYPE_CLOB)
                cursor.executemany(_SQL_UPSERT, lote)
            if retirados:
                cursor.executemany(
                    "DELETE FROM conjunto_consultable WHERE id = :id",
                    [{"id": identificador} for identificador in retirados],
                )
            cursor.execute(
                _SQL_META,
                {
                    "version": documento["version"],
                    "total": len(lote),
                    "total_spam_excluido": documento.get(
                        "total_spam_excluido", 0
                    ),
                },
            )
        conexion.commit()
        return len(retirados)
    except Exception:
        conexion.rollback()
        raise


def _leer_filas_con_texto(cursor) -> list[tuple]:
    cursor.execute(_SQL_SELECT_TODOS)
    filas = []
    for fila in cursor.fetchall():
        valores = list(fila)
        # Materializar el CLOB antes de cerrar cursor/conexión, sin cambiar
        # las preferencias globales del driver para otros consumidores.
        contenido = valores[8]
        if isinstance(contenido, oracledb.LOB):
            contenido = contenido.read()
            if not isinstance(contenido, str):
                raise ValueError("contenido_textual debe ser un CLOB de texto, no binario")
            valores[8] = contenido
        filas.append(tuple(valores))
    return filas


def leer_conjunto(
    *,
    conexion: oracledb.Connection | None = None,
) -> dict[str, Any]:
    """Lee filas y metadatos en una sola consulta consistente y sin commit.

    Para el agente, inyectar una conexión de solo SELECT, con acceso a ambas
    tablas. No conectar el agente público con el usuario cargador por defecto.
    """
    if conexion is not None:
        with conexion.cursor() as cursor:
            filas = _leer_filas_con_texto(cursor)
    else:
        with (
            obtener_conexion_lectura() as conexion_activa,
            conexion_activa.cursor() as cursor,
        ):
            filas = _leer_filas_con_texto(cursor)

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
