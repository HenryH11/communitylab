"""Publicacion explicita de un lote revisado desde la aplicacion interna.

Reutiliza los contratos de DS y DA. La UI no obtiene el secreto escritor ni
abre una conexion Oracle: envia JSON al ingestor privado, sin reintentos
automaticos. Este modulo no hace llamadas al importarse.
"""

from hashlib import sha256
from http.client import HTTPException
import ipaddress
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from src.agentes.entrega_resultados import preparar_entrega_resultados
from src.datos.conjunto_consultable import construir_conjunto_consultable


class ErrorPublicacion(RuntimeError):
    """Error seguro para mostrar sin respuestas crudas, credenciales ni URL."""


def preparar_publicacion(resultado: dict, mensajes: dict) -> dict:
    """Convierte solo un procesamiento completo al Conjunto Consultable."""
    entrega = preparar_entrega_resultados(resultado)
    if entrega["pendientes"] or entrega["ids_pendientes"] or any(
        fila.get("errores") or fila.get("fallos")
        for fila in entrega["interacciones"]
    ):
        raise ValueError("Completa o corrige el procesamiento antes de publicar el lote.")
    if not entrega["interacciones"]:
        raise ValueError("No hay interacciones procesadas para publicar.")
    documento = construir_conjunto_consultable(entrega, mensajes)
    # Fallar antes del envio, no despues de iniciar una transaccion en Oracle.
    for fila in documento["registros"]:
        for campo in ("canal", "sentimiento", "tema", "tipo"):
            if not isinstance(fila[campo], str) or not fila[campo].strip():
                raise ValueError(f"El lote tiene un campo {campo} incompleto.")
    return documento


def _url_interna(url: str) -> str:
    try:
        partes = urlsplit(url)
        puerto = partes.port
        host = partes.hostname
        if (
            partes.scheme not in {"http", "https"}
            or not host or partes.username is not None or partes.password is not None
            or partes.query or partes.fragment or partes.path != "/sincronizar"
            or (puerto is not None and not 1 <= puerto <= 65535)
        ):
            raise ValueError
        if host != "localhost":
            ip = ipaddress.ip_address(host)
            redes = ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fc00::/7")
            if not ip.is_loopback and not any(ip in ipaddress.ip_network(n) for n in redes):
                raise ValueError
    except (ValueError, TypeError):
        raise ErrorPublicacion(
            "Configura INGESTOR_URL con una IP privada o localhost y la ruta /sincronizar."
        ) from None
    return url


class _SinRedirecciones(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def publicar_conjunto(documento: dict, *, url: str | None = None, opener=None) -> dict:
    """Una unica peticion; un timeout nunca se interpreta como guardado exitoso."""
    destino = _url_interna(url if url is not None else os.getenv("INGESTOR_URL", ""))
    try:
        cuerpo = json.dumps(documento, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError):
        raise ErrorPublicacion("El lote no se puede enviar como JSON válido.") from None
    solicitud = Request(destino, data=cuerpo, headers={
        "Content-Type": "application/json; charset=utf-8", "Accept": "application/json",
    }, method="POST")
    # No enviar datos por proxies heredados ni seguir un redirect del servidor.
    cliente = opener if opener is not None else build_opener(ProxyHandler({}), _SinRedirecciones())
    try:
        with cliente.open(solicitud, timeout=15) as respuesta:
            if respuesta.status != 200:
                raise ValueError
            contenido = respuesta.read(65537)
            if len(contenido) > 65536:
                raise ValueError
            recibo = json.loads(contenido)
    except HTTPError as error:
        error.close()
        if error.code == 400:
            raise ErrorPublicacion(
                "El ingestor rechazó el lote. Revisa sus campos y los IDs ya publicados."
            ) from None
        raise ErrorPublicacion(
            "El ingestor no confirmó la publicación. Conserva el lote para revisarlo o reintentarlo."
        ) from None
    except (URLError, TimeoutError, OSError, ValueError, HTTPException):
        raise ErrorPublicacion(
            "Sin confirmación de guardado. Reintenta el mismo lote, sin volver a procesarlo con IA."
        ) from None
    campos = ("sincronizados", "insertados", "retirados", "total", "total_spam_excluido")
    if (
        not isinstance(recibo, dict)
        or recibo.get("tabla") != "conjunto_consultable"
        or any(type(recibo.get(c)) is not int or recibo[c] < 0 for c in campos)
        or type(recibo.get("repetido")) is not bool
        or recibo["sincronizados"] != documento["total"]
        or recibo["retirados"] != 0
        or recibo["insertados"] > documento["total"]
        or recibo["total"] < documento["total"]
        or recibo["total_spam_excluido"] < documento["total_spam_excluido"]
        or (recibo["repetido"] and recibo["insertados"] != 0)
    ):
        raise ErrorPublicacion("La respuesta no permite confirmar el guardado del lote.")
    return {c: recibo[c] for c in ("tabla", *campos, "repetido")}


def render(resultado: dict, mensajes: dict) -> None:
    """Se invoca exclusivamente desde Datos, despues de un procesamiento exitoso."""
    import streamlit as st

    st.subheader("Publicar el lote revisado en Oracle")
    try:
        documento = preparar_publicacion(resultado, mensajes)
    except (ValueError, TypeError, KeyError):
        st.warning("El lote no está completo o tiene errores. Revísalo antes de publicarlo.")
        return
    firma = sha256(json.dumps(documento, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    recibos = st.session_state.setdefault("_recibos_publicacion_oracle", {})
    st.caption(
        f"Último lote procesado: {documento['total']} mensajes consultables; "
        f"{documento['total_spam_excluido']} excluidos por spam. "
        "La publicación conserva los lotes anteriores y no publica en redes."
    )
    with st.expander("Revisar los mensajes que se enviarán"):
        st.dataframe(documento["registros"], hide_index=True, width="stretch")
    confirmado = st.checkbox(
        "Revisé el lote y confirmo su publicación en Oracle",
        key="confirmar_publicacion_oracle_" + firma,
    )
    configurado = bool(os.getenv("INGESTOR_URL", "").strip())
    if not configurado:
        st.info("Falta configurar el acceso privado al ingestor en esta app interna.")
    pulsado = st.button("Publicar lote en Oracle", key="publicar_lote_oracle",
                        disabled=not confirmado or not configurado or firma in recibos)
    if pulsado and confirmado and configurado and firma not in recibos:
        try:
            recibos[firma] = publicar_conjunto(documento)
        except ErrorPublicacion as error:
            st.error(str(error))
    if firma in recibos:
        recibo = recibos[firma]
        if recibo["repetido"]:
            st.success("Este lote ya estaba publicado. No se duplicaron registros ni spam.")
        else:
            st.success(
                f"Publicación confirmada: {recibo['insertados']} mensajes nuevos; "
                f"{recibo['total']} mensajes en Oracle al publicar."
            )
