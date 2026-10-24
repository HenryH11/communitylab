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
