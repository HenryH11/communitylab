"""Carga interna de lotes en INSUMOS, fuera del cliente público de lectura.

Conserva los lotes anteriores y registra sus huellas para no duplicar el
contador de spam en reintentos. No ejecuta DDL ni crea permisos en OCI.
"""

import base64
from collections.abc import Mapping, Sequence
from datetime import datetime
from functools import lru_cache
import hashlib
import io
import json
import logging
import os
import re
from typing import Any

from oci.auth.signers import (
    InstancePrincipalsSecurityTokenSigner,
    get_resource_principals_signer,
)
from oci.secrets import SecretsClient
import oracledb

oracledb.defaults.fetch_lobs = False

LOGGER = logging.getLogger(__name__)

USUARIO_PREDETERMINADO = "rw_ingest_communitylab"
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

_SQL_FILAS = """
SELECT id, canal, sentimiento, tema, tipo, contenido_textual,
       CASE WHEN fecha IS NOT NULL THEN
           TO_CHAR(fecha AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"')
       ELSE NULL END
FROM conjunto_consultable
"""
_SQL_LEER_META = (
    "SELECT version, total, total_spam_excluido "
    "FROM conjunto_consultable_meta WHERE id = 1"
)
_SQL_CARGA = (
    "SELECT huella FROM conjunto_consultable_cargas WHERE huella = :huella"
)
_SQL_REGISTRAR_CARGA = """
INSERT INTO conjunto_consultable_cargas
    (huella, version, total, total_spam_excluido)
VALUES (:huella, :version, :total, :total_spam_excluido)
"""


@lru_cache(maxsize=1)
def obtener_cliente_secretos() -> SecretsClient:
    """Inicializa y almacena en caché el cliente de secretos de OCI.

    Usa Resource Principals cuando se ejecuta en OCI Functions y
    recurre a Instance Principals en entornos de cómputo estándar.
    """
    if os.getenv("OCI_RESOURCE_PRINCIPAL_VERSION"):
        signer = get_resource_principals_signer()
    else:
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
    """Recupera un secreto en texto plano desde OCI Vault."""
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

    for campo in ("canal", "sentimiento", "tema", "tipo"):
        valor = registro[campo]
        if not isinstance(valor, str) or not valor.strip():
            raise ValueError(f"{campo} debe ser texto no vacío, no null")

    contenido = registro["contenido_textual"]
    if not isinstance(contenido, str) or not contenido:
        raise ValueError("contenido_textual debe ser texto completo no vacío")

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


def _huella_lote(
    documento: Mapping[str, Any], lote: list[dict[str, Any]]
) -> str:
    """Identifica el documento completo sin depender del orden de sus filas."""
    canonico = {
        "version": documento["version"],
        "total_spam_excluido": documento.get("total_spam_excluido", 0),
        "registros": sorted(lote, key=lambda registro: registro["id"]),
    }
    datos = json.dumps(
        canonico, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(datos).hexdigest()


def _publicar_lote(
    conexion: oracledb.Connection,
    documento: Mapping[str, Any],
    lote: list[dict[str, Any]],
) -> dict[str, str | int | bool]:
    """Agrega filas y confirma datos, metadatos y recibo en una transacción."""
    if conexion.autocommit or conexion.transaction_in_progress:
        raise ValueError(
            "usa una conexión exclusiva sin transacción activa "
            "y sin autocommit"
        )
    try:
        with conexion.cursor() as cursor:
            cursor.execute(
                "LOCK TABLE conjunto_consultable, conjunto_consultable_meta, "
                "conjunto_consultable_cargas "
                "IN EXCLUSIVE MODE NOWAIT"
            )
            cursor.execute(_SQL_FILAS)
            actuales = {
                fila[0]: dict(zip(CAMPOS_CONJUNTO, fila))
                for fila in cursor.fetchall()
            }
            cursor.execute(_SQL_LEER_META)
            metadatos = cursor.fetchall()
            if metadatos:
                version, total_anterior, spam_anterior = metadatos[0]
                if total_anterior != len(actuales):
                    raise ValueError(
                        "metadatos no coincide con las filas existentes"
                    )
                if version not in ("1.0", VERSION_CONJUNTO):
                    raise ValueError("versión almacenada no admitida")
                if type(spam_anterior) is not int or spam_anterior < 0:
                    raise ValueError("contador de spam almacenado inválido")
            elif actuales:
                raise ValueError(
                    "hay filas existentes sin metadatos; revisar antes de cargar"
                )
            else:
                spam_anterior = 0

            nuevos = []
            for registro in lote:
                anterior = actuales.get(registro["id"])
                if anterior is not None and anterior != registro:
                    raise ValueError(
                        f"conflicto de contenido para id {registro['id']}; "
                        "no se sobrescriben registros existentes"
                    )
                if anterior is None:
                    nuevos.append(registro)

            huella = _huella_lote(documento, lote)
            cursor.execute(_SQL_CARGA, {"huella": huella})
            repetido = bool(cursor.fetchall())
            if repetido and nuevos:
                raise ValueError(
                    "el recibo del lote no coincide con las filas existentes"
                )
            if nuevos:
                cursor.setinputsizes(contenido_textual=oracledb.DB_TYPE_CLOB)
                cursor.executemany(_SQL_UPSERT, nuevos)
            spam_lote = documento.get("total_spam_excluido", 0)
            # Sin recibo no se puede atribuir con certeza el spam de un lote
            # que solapa otro. Rechazar evita sumar dos veces o inventar cifras.
            if not repetido and len(nuevos) != len(lote) and spam_lote:
                raise ValueError(
                    "lote solapado sin recibo y con spam; requiere conciliación"
                )
            total = len(actuales) + len(nuevos)
            spam = spam_anterior + (0 if repetido else spam_lote)
            cursor.execute(
                _SQL_META,
                {
                    "version": VERSION_CONJUNTO,
                    "total": total,
                    "total_spam_excluido": spam,
                },
            )
            if not repetido:
                cursor.execute(
                    _SQL_REGISTRAR_CARGA,
                    {
                        "huella": huella,
                        "version": documento["version"],
                        "total": len(lote),
                        "total_spam_excluido": spam_lote,
                    },
                )
        conexion.commit()
        return {
            "tabla": TABLA_PREDETERMINADA,
            "sincronizados": len(lote),
            "insertados": len(nuevos),
            "retirados": 0,
            "total": total,
            "total_spam_excluido": spam,
            "repetido": repetido,
        }
    except Exception:
        conexion.rollback()
        raise


def sincronizar_conjunto(
    documento: Mapping[str, Any],
    *,
    conexion: oracledb.Connection | None = None,
    instantanea_completa: bool = False,
) -> dict[str, str | int | bool]:
    """Agrega un lote completo sin borrar otros lotes ni sobrescribir IDs.

    ``instantanea_completa`` confirma que el documento está completo, NO
    autoriza reemplazar la tabla. Los reintentos se identifican por huella.
    """
    lote = _preparar_lote(documento)
    if instantanea_completa is not True:
        raise ValueError(
            "confirma instantanea_completa=True; no se admiten lotes parciales"
        )

    if conexion is not None:
        return _publicar_lote(conexion, documento, lote)
    else:
        with obtener_conexion() as conexion_activa:
            return _publicar_lote(conexion_activa, documento, lote)


def handler(ctx: Any, data: io.BytesIO | None = None) -> Any:
    """Adaptador opcional de Functions; la carga no depende del FDK."""
    from fdk import response

    try:
        if data is None:
            raise ValueError("el cuerpo de la petición está vacío")

        cuerpo_raw = data.getvalue().decode("utf-8")
        documento = json.loads(cuerpo_raw)
        resultado = sincronizar_conjunto(
            documento,
            instantanea_completa=True,
        )
        return response.Response(
            ctx,
            response_data=json.dumps(resultado),
            headers={"Content-Type": "application/json"},
            status_code=200,
        )
    except (ValueError, TypeError, json.JSONDecodeError) as error_validacion:
        LOGGER.warning("Error de validación en ingesta: %s", error_validacion)
        return response.Response(
            ctx,
            response_data=json.dumps({"error": str(error_validacion)}),
            headers={"Content-Type": "application/json"},
            status_code=400,
        )
    except Exception as error_interno:
        LOGGER.error(
            "Fallo crítico durante la ingesta (%s)",
            type(error_interno).__name__,
        )
        return response.Response(
            ctx,
            response_data=json.dumps(
                {"error": "error interno al sincronizar la instantánea"}
            ),
            headers={"Content-Type": "application/json"},
            status_code=500,
        )
