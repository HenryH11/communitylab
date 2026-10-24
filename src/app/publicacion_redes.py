"""Preparación de contenido para abrir redes sin publicar ni conectar cuentas."""

import re
from urllib.parse import urlencode, urlsplit

import streamlit as st

from src.agentes.plataformas import NOMBRES_PLATAFORMA, texto_publicacion


REDES = {
    "linkedin": ("LinkedIn", "https://www.linkedin.com/feed/"),
    "instagram": ("Instagram", "https://www.instagram.com/"),
    "x": ("X", "https://twitter.com/intent/tweet"),
    "facebook": ("Facebook", "https://www.facebook.com/"),
    "whatsapp": ("WhatsApp", "https://wa.me/"),
    "telegram": ("Telegram", "https://t.me/"),
    "threads": ("Threads", "https://www.threads.com/intent/post"),
    "bluesky": ("Bluesky", "https://bsky.app/intent/compose"),
    "mastodon": ("Mastodon", ""),
}

LIMITES_TEXTO = {"x": 280, "threads": 500, "bluesky": 300}


def validar_url(valor: str, *, servidor: bool = False) -> str:
    valor = valor.strip()
    mensaje = (
        "Introduce el origen HTTPS de tu servidor, por ejemplo https://mastodon.social, "
        "sin rutas, credenciales ni parámetros."
        if servidor else "Introduce un enlace HTTP o HTTPS válido, sin credenciales."
    )
    try:
        partes = urlsplit(valor)
        host = (partes.hostname or "").encode("idna").decode("ascii")
        puerto = partes.port
    except (ValueError, UnicodeError) as error:
        raise ValueError(mensaje) from error
    if (
        partes.scheme not in ({"https"} if servidor else {"http", "https"})
        or not host
        or any(not re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", p)
               for p in host.split("."))
        or partes.username is not None or partes.password is not None
        or any(c.isspace() or ord(c) < 32 for c in valor)
        or "\\" in valor
        or (puerto is not None and puerto < 1)
        or (servidor and (partes.path not in {"", "/"} or partes.query or partes.fragment))
    ):
        raise ValueError(mensaje)
    return valor.rstrip("/") if servidor else valor


def enlace_publicacion(
    publicacion: dict, *, enlace: str = "", servidor: str = "",
) -> str:
    texto = texto_publicacion(publicacion)
    plataforma = publicacion["plataforma"]
    url = REDES[plataforma][1]
    if plataforma == "mastodon":
        return f"{validar_url(servidor, servidor=True)}/share?{urlencode({'text': texto})}"
    if plataforma in {"x", "threads", "bluesky", "whatsapp"}:
        return f"{url}?{urlencode({'text': texto})}"
    if plataforma == "facebook" and enlace:
        return "https://www.facebook.com/sharer/sharer.php?" + urlencode({
            "u": validar_url(enlace),
        })
    if plataforma == "telegram" and enlace:
        return "https://t.me/share/url?" + urlencode({
            "url": validar_url(enlace), "text": texto,
        })
    return url


def render(publicacion: dict, *, clave: str = "publicacion") -> None:
    texto = texto_publicacion(publicacion)
    plataforma = publicacion["plataforma"]
    nombre = NOMBRES_PLATAFORMA[plataforma]
    enlace = ""
    servidor = ""
    if plataforma in {"facebook", "telegram"}:
        enlace = st.text_input(
            "Enlace para compartir (opcional)", key=f"{clave}_enlace",
            placeholder="https://ejemplo.com/articulo",
            help="Añade un enlace real. No se inventan enlaces a partir de las fuentes.",
        ).strip()
    elif plataforma == "mastodon":
        servidor = st.text_input(
            "Servidor de tu cuenta de Mastodon", key=f"{clave}_servidor",
            placeholder="https://mastodon.social",
            help="Usa el servidor donde tienes tu cuenta; no todos pertenecen al mismo.",
        ).strip()

    precarga = plataforma in {"x", "threads", "bluesky", "whatsapp", "mastodon"}
    precarga = precarga or (plataforma == "telegram" and bool(enlace))
    if precarga:
        with st.expander(f"Copiar texto si {nombre} no lo precarga"):
            st.code(texto, language=None, wrap_lines=True, height=140)
    else:
        with st.expander(f"Copiar publicación para {nombre}", expanded=True):
            st.caption("Usa el botón de copiar del recuadro; después abre la red y pega el texto.")
            st.code(texto, language=None, wrap_lines=True, height=140)

    if plataforma == "mastodon" and not servidor:
        st.info("Introduce el servidor de tu cuenta para abrir el editor de Mastodon.")
        return
    try:
        url = enlace_publicacion(publicacion, enlace=enlace, servidor=servidor)
    except ValueError as error:
        st.warning(str(error))
        return

    if precarga:
        st.link_button(
            (
                f"Preparar mensaje en {nombre}"
                if plataforma in {"whatsapp", "telegram"}
                else f"Preparar publicación en {nombre}"
            ), url,
            icon=":material/open_in_new:",
            help="Abre el editor con el texto. Revisa y confirma allí.",
        )
        st.caption(
            "Elige el chat, grupo o canal, revisa el mensaje y confirma el envío allí."
            if plataforma in {"whatsapp", "telegram"}
            else f"Se abrirá {nombre} con el texto preparado. Revisa y confirma allí."
        )
    else:
        st.link_button(
            "Compartir enlace en Facebook" if plataforma == "facebook" and enlace
            else f"Abrir {nombre}", url,
            icon=":material/open_in_new:",
            help="Abre la red social; el texto no se pega automáticamente.",
        )
        instrucciones = {
            "instagram": "Instagram necesita una imagen o video: añádelo y pega este texto como descripción.",
            "linkedin": "En LinkedIn, inicia una publicación y pega el texto copiado.",
            "facebook": "Facebook comparte el enlace, pero no garantiza precargar texto libre. Copia y pega el texto.",
            "telegram": "El botón oficial de Telegram requiere un enlace. Añádelo arriba o copia el mensaje y elige dónde enviarlo.",
        }
        st.caption(instrucciones[plataforma])
        st.caption("Abrir la red no publica el contenido. Revisa y confirma allí.")

    limite = LIMITES_TEXTO.get(plataforma)
    if limite is not None and len(texto) > limite:
        st.warning(
            f"El contenido con sus etiquetas supera {limite} caracteres "
            f"en el conteo local. Pide una versión más corta y revisa el límite que muestre {nombre}. "
            "El texto no se recorta automáticamente."
        )
