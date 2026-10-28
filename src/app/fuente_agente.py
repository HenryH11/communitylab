"""Fuente de datos del agente en vivo.

El agente no escribe en la base: toma una captura completa del Conjunto
Consultable una vez por sesión y solo la renueva cuando pasa la vigencia
(1 hora). El usuario puede sumar archivos propios, que viven únicamente en su
sesión y se combinan con la captura al consultar.

Los mensajes de error son para el usuario final: nunca mencionan código,
variables de entorno ni nombres de tablas. El detalle técnico va al log.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping, MutableMapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import PurePath
from typing import Any

VIGENCIA_CAPTURA = timedelta(hours=1)
# Tras un fallo no se reintenta en cada interacción de la página.
ESPERA_REINTENTO = timedelta(minutes=2)
CLAVE_CAPTURA = "captura_base_comunidad"

MAX_BYTES_ARCHIVO = 5 * 1024 * 1024
MAX_MENSAJES_ARCHIVO = 5_000
MAX_CARACTERES_MENSAJE = 50_000
FORMATOS_ARCHIVO = ("json", "csv", "txt")

NO_CONFIGURADA = (
    "La base de datos de la comunidad todavía no está conectada a esta "
    "instalación. Avisa al administrador de CommunityLab."
)
SIN_PUBLICAR = (
    "La base de datos de la comunidad aún no tiene información publicada. "
    "El equipo de CommunityLab la cargará pronto."
)
EN_ACTUALIZACION = (
    "La base de datos de la comunidad se está actualizando en este momento. "
    "Intenta de nuevo en unos minutos."
)
SIN_CONEXION = (
    "No fue posible conectarse a la base de datos de la comunidad. Intenta de "
    "nuevo en unos minutos; si continúa, avisa al administrador de CommunityLab."
)

_COLUMNAS_TEXTO = (
    "texto", "contenido", "contenido_textual", "contenido_corto", "mensaje", "comentario",
    "comentarios", "text", "content", "message", "comment", "body", "post",
)
_COLUMNAS_OPCIONALES = {
    "autor": ("autor", "author", "usuario", "user", "username", "nombre"),
    "canal": ("canal", "channel", "plataforma", "platform", "red", "red_social", "fuente"),
    "fecha": ("fecha", "date", "created_at", "timestamp", "fecha_publicacion"),
    "sentimiento": ("sentimiento", "sentiment"),
    "tema_principal": ("tema_principal", "tema", "topic", "categoria"),
}
_CLAVES_LISTA = (
    "interacciones", "resultados", "registros", "mensajes", "comentarios",
    "data", "items",
)

_log = logging.getLogger(__name__)


class FuenteNoDisponible(Exception):
    """La base de la comunidad no se pudo leer; el mensaje es apto para el usuario."""


@dataclass(frozen=True)
class Captura:
    mensajes: tuple[dict[str, Any], ...]
    capturada_en: datetime
    desactualizada: bool = False
    aviso: str = ""


def _fecha_iso(valor: object) -> str:
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            valor = valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(valor, date):
        return valor.isoformat()
    return valor.strip() if isinstance(valor, str) else ""


def _texto(valor: object) -> str:
    return valor.strip() if isinstance(valor, str) else ""


def adaptar_conjunto(documento: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Convierte la instantánea de la base al formato de mensajes del agente."""
    registros = documento.get("registros") if isinstance(documento, Mapping) else None
    if not isinstance(registros, list):
        raise ValueError("la instantánea no contiene una lista de registros")
    mensajes = []
    vistos: set[str] = set()
    for registro in registros:
        if not isinstance(registro, Mapping):
            continue
        identificador = _texto(registro.get("id"))
        texto = registro.get("contenido_textual")
        if (
            not identificador or not isinstance(texto, str)
            or not texto.strip() or identificador in vistos
        ):
            continue
        vistos.add(identificador)
        mensajes.append(
            {
                "id": identificador,
                "texto": texto,
                "autor": _texto(registro.get("autor")),
                "canal": _texto(registro.get("canal")),
                "sentimiento": _texto(registro.get("sentimiento")),
                "tema_principal": _texto(registro.get("tema")),
                "tipo_detectado": _texto(registro.get("tipo")),
                "fecha": _fecha_iso(registro.get("fecha")),
            }
        )
    return mensajes


def leer_base() -> Mapping[str, Any]:
    """Lee la instantánea publicada con el usuario de solo lectura."""
    try:
        # Importación diferida: sin los paquetes de Oracle/OCI la app sigue viva.
        from src.config import db_client
    except ImportError as error:
        raise FuenteNoDisponible(NO_CONFIGURADA) from error
    try:
        conexion = db_client.obtener_conexion_lectura()
    except ValueError as error:
        raise FuenteNoDisponible(NO_CONFIGURADA) from error
    except Exception as error:
        raise FuenteNoDisponible(SIN_CONEXION) from error
    try:
        with conexion:
            return db_client.leer_conjunto(conexion=conexion)
    except ValueError as error:
        if "metadatos" in str(error):
            raise FuenteNoDisponible(SIN_PUBLICAR) from error
        raise FuenteNoDisponible(EN_ACTUALIZACION) from error
    except Exception as error:
        raise FuenteNoDisponible(SIN_CONEXION) from error


def obtener_captura(
    estado: MutableMapping[Any, Any],
    *,
    lector: Callable[[], Mapping[str, Any]] | None = None,
    ahora: datetime | None = None,
    vigencia: timedelta = VIGENCIA_CAPTURA,
    forzar: bool = False,
) -> Captura:
    """Devuelve la captura de la sesión y solo vuelve a la base al vencer.

    Si la lectura falla y existe una captura previa, se sigue usando marcada
    como desactualizada. Sin captura previa se lanza ``FuenteNoDisponible``.
    """
    ahora = ahora or datetime.now(timezone.utc)
    registro = estado.get(CLAVE_CAPTURA)
    previa: Captura | None = registro["captura"] if registro else None
    if registro and not forzar:
        if registro["error"] is None and previa is not None:
            if ahora - previa.capturada_en < vigencia:
                return previa
        elif ahora - registro["intentado_en"] < ESPERA_REINTENTO:
            if previa is not None:
                return replace(previa, desactualizada=True, aviso=registro["error"])
            raise FuenteNoDisponible(registro["error"])

    try:
        mensajes = adaptar_conjunto((lector or leer_base)())
    except FuenteNoDisponible as error:
        _log.warning("No se pudo leer la base de la comunidad", exc_info=error)
        aviso = str(error)
    except ValueError as error:
        _log.warning("La instantánea de la base no es válida", exc_info=error)
        aviso = EN_ACTUALIZACION
    except Exception as error:
        _log.warning("Fallo inesperado al leer la base", exc_info=error)
        aviso = SIN_CONEXION
    else:
        captura = Captura(tuple(mensajes), ahora)
        estado[CLAVE_CAPTURA] = {"captura": captura, "error": None, "intentado_en": ahora}
        return captura

    estado[CLAVE_CAPTURA] = {"captura": previa, "error": aviso, "intentado_en": ahora}
    if previa is not None:
        return replace(previa, desactualizada=True, aviso=aviso)
    raise FuenteNoDisponible(aviso)


def _clave(nombre: object) -> str:
    sin_acentos = unicodedata.normalize("NFKD", str(nombre).strip().casefold())
    plano = "".join(c for c in sin_acentos if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "_", plano).strip("_")


def _prefijo(nombre_archivo: str) -> str:
    base = _clave(PurePath(nombre_archivo).stem).replace("_", "-")
    return (base or "archivo")[:24].strip("-") or "archivo"


def _columna(columnas: Iterable[str], candidatas: Iterable[str]) -> str | None:
    por_clave = {_clave(columna): columna for columna in columnas}
    return next((por_clave[c] for c in candidatas if c in por_clave), None)


def _desde_filas(filas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columnas = list(dict.fromkeys(c for fila in filas for c in fila if isinstance(c, str)))
    texto = _columna(columnas, _COLUMNAS_TEXTO)
    if texto is None:
        # Sin un nombre reconocible, se toma la columna con textos más largos.
        promedios = {
            columna: sum(len(str(f.get(columna) or "")) for f in filas) / max(len(filas), 1)
            for columna in columnas
        }
        texto = max(promedios, key=lambda columna: promedios[columna], default=None)
    if texto is None:
        return []
    opcionales = {
        campo: _columna(columnas, candidatas)
        for campo, candidatas in _COLUMNAS_OPCIONALES.items()
    }
    mensajes = []
    for fila in filas:
        contenido = fila.get(texto)
        if not isinstance(contenido, str) or not contenido.strip():
            continue
        mensaje = {"texto": contenido.strip()}
        for campo, columna in opcionales.items():
            if columna is not None and columna != texto:
                valor = fila.get(columna)
                mensaje[campo] = _fecha_iso(valor) if campo == "fecha" else _texto(valor)
        mensajes.append(mensaje)
    return mensajes


def _elementos_json(datos: object) -> list[object]:
    if isinstance(datos, list):
        return datos
    if not isinstance(datos, dict):
        return []
    if isinstance(datos.get("lotes"), list):
        return [
            elemento
            for lote in datos["lotes"]
            if isinstance(lote, dict)
            for elemento in _elementos_json(lote)
        ]
    for clave in _CLAVES_LISTA:
        if isinstance(datos.get(clave), list):
            return datos[clave]
    if isinstance(datos.get("resultados_por_id"), dict):
        return list(datos["resultados_por_id"].values())
    return [datos]


def leer_archivo_usuario(nombre: str, contenido: bytes) -> list[dict[str, Any]]:
    """Extrae mensajes de un JSON, CSV o TXT sin exigir una estructura fija."""
    extension = PurePath(nombre).suffix.lower().lstrip(".")
    if extension not in FORMATOS_ARCHIVO:
        raise ValueError(
            f"«{nombre}» no es compatible. Adjunta archivos JSON, CSV o TXT."
        )
    if len(contenido) > MAX_BYTES_ARCHIVO:
        raise ValueError(f"«{nombre}» supera el máximo de 5 MB por archivo.")
    try:
        texto = contenido.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            texto = contenido.decode("cp1252")
        except UnicodeDecodeError as error:
            raise ValueError(f"No pude leer «{nombre}» como texto.") from error

    if extension == "json":
        try:
            datos = json.loads(texto)
        except json.JSONDecodeError as error:
            raise ValueError(f"«{nombre}» no es un JSON válido.") from error
        elementos = _elementos_json(datos)
        filas = [e for e in elementos if isinstance(e, dict)]
        mensajes = _desde_filas(filas)
        mensajes += [
            {"texto": e.strip()} for e in elementos if isinstance(e, str) and e.strip()
        ]
    elif extension == "csv":
        try:
            dialecto: Any = csv.Sniffer().sniff(texto[:4096], delimiters=",;\t|")
        except csv.Error:
            dialecto = csv.excel
        mensajes = _desde_filas(list(csv.DictReader(io.StringIO(texto), dialect=dialecto)))
    else:
        mensajes = [{"texto": linea.strip()} for linea in texto.splitlines() if linea.strip()]

    if not mensajes:
        raise ValueError(f"No encontré mensajes con texto en «{nombre}».")
    if len(mensajes) > MAX_MENSAJES_ARCHIVO:
        limite = f"{MAX_MENSAJES_ARCHIVO:,}".replace(",", ".")
        raise ValueError(
            f"«{nombre}» tiene más de {limite} mensajes; "
            "divídelo en archivos más pequeños."
        )
    prefijo = _prefijo(nombre)
    for numero, mensaje in enumerate(mensajes, start=1):
        mensaje["id"] = f"{prefijo}-{numero}"
        mensaje["texto"] = mensaje["texto"][:MAX_CARACTERES_MENSAJE]
    return mensajes


def combinar(
    base: Iterable[Mapping[str, Any]],
    archivos: Mapping[str, Iterable[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    """Une la captura con los archivos del usuario sin repetir identificadores."""
    combinados = [dict(mensaje) for mensaje in base]
    usados = {mensaje["id"] for mensaje in combinados}
    for mensajes in archivos.values():
        for mensaje in mensajes:
            copia = dict(mensaje)
            identificador, sufijo = copia["id"], 2
            while identificador in usados:
                identificador, sufijo = f"{copia['id']}-{sufijo}", sufijo + 1
            copia["id"] = identificador
            usados.add(identificador)
            combinados.append(copia)
    return combinados
