"""Destinos de texto admitidos por el agente y la interfaz de publicación."""

from typing import Literal


PlataformaPublicacion = Literal[
    "linkedin", "instagram", "x", "facebook", "whatsapp", "telegram",
    "threads", "bluesky", "mastodon",
]

NOMBRES_PLATAFORMA: dict[str, str] = {
    "linkedin": "LinkedIn",
    "instagram": "Instagram",
    "x": "X",
    "facebook": "Facebook",
    "whatsapp": "WhatsApp",
    "telegram": "Telegram",
    "threads": "Threads",
    "bluesky": "Bluesky",
    "mastodon": "Mastodon",
}


def texto_publicacion(publicacion: dict) -> str:
    plataforma = publicacion.get("plataforma")
    if plataforma not in NOMBRES_PLATAFORMA:
        raise ValueError("La red social de esta publicación no es compatible.")
    campos = ["contenido"] if plataforma == "x" else ["titulo", "contenido"]
    partes = [
        publicacion[campo].strip()
        for campo in campos
        if isinstance(publicacion.get(campo), str) and publicacion[campo].strip()
    ]
    if not partes:
        raise ValueError("La publicación necesita contenido antes de abrir la red social.")
    hashtags = publicacion.get("hashtags", [])
    if not isinstance(hashtags, list) or any(not isinstance(h, str) for h in hashtags):
        raise ValueError("Revisa las etiquetas de la publicación.")
    etiquetas = " ".join(h.strip() for h in hashtags if h.strip())
    if etiquetas:
        partes.append(etiquetas)
    return "\n\n".join(partes)
