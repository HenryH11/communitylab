"""Limpieza, normalización y preservación de texto y Unicode."""

import html
import re
import unicodedata

# Lista acotada: conserva expresiones técnicas como a < b y tipos como <T>.
ETIQUETAS = re.compile(
    r"</?(?:p|div|span|br|a|b|strong|em|i|ul|ol|li|pre|code|blockquote|h[1-6])\b[^>]*>",
    re.IGNORECASE,
)

_CATEGORIAS_CONTROL = {"Cc", "Cf"}

# Detecta secuencias típicas de mojibake (UTF-8 interpretado como Latin-1 / Windows-1252)
# Por ejemplo: Ã© (é), Ã± (ñ), Â¿ (¿), Â¡ (¡), â€œ (“), etc.
PATRON_MOJIBAKE = re.compile(
    r"(?:[\u00c2\u00c3][\u0080-\u00ff]|[\u00e2][\u0080-\u00ff]{2})+"
)


def detectar_mojibake(texto: str) -> bool:
    """Verifica si el texto contiene secuencias típicas de mojibake."""
    if not isinstance(texto, str):
        return False
    return bool(PATRON_MOJIBAKE.search(texto))


def reparar_mojibake(texto: str) -> str:
    """Repara secuencias de mojibake (UTF-8 interpretado como Latin-1/CP1252).

    Si el texto no contiene secuencias de mojibake, se devuelve intacto.
    """
    if not isinstance(texto, str) or not detectar_mojibake(texto):
        return texto

    # Intento 1: Cadena completa (caso más común cuando todo el texto fue mal decodificado)
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Intento 2: Reparación selectiva por fragmentos (cuando coexisten caracteres externos como emojis)
    def _arreglar_coincidencia(match: re.Match) -> str:
        pedazo = match.group(0)
        try:
            return pedazo.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return pedazo

    return PATRON_MOJIBAKE.sub(_arreglar_coincidencia, texto)


def _texto_visible(texto: str) -> str:
    """Decodifica HTML y elimina solo el marcado que la limpieza admite."""
    texto = unicodedata.normalize("NFC", html.unescape(texto))
    texto = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", " ", texto, flags=re.I | re.S)
    return ETIQUETAS.sub(" ", texto)


def limpiar_texto(texto: str, reparar_encoding: bool = True) -> str:
    """Limpia HTML, scripts, caracteres de control y normaliza espacios.

    Opcionalmente repara mojibake si se detecta texto mal decodificado.
    """
    if reparar_encoding:
        texto = reparar_mojibake(texto)
    texto = _texto_visible(texto)
    texto = "".join(
        " " if unicodedata.category(c) == "Cc" or c == "\ufffd" else c
        for c in texto if c not in {"\u200b", "\ufeff"}
    )
    return " ".join(texto.split())


def estimar_tokens(texto: str) -> int:
    """Aproxima el consumo de tokens de un texto (~4 caracteres por token).

    Solo estima el texto. No incluye prompts, metadatos, respuestas ni
    reintentos, por lo que no representa cuota ni facturación de Gemini.
    """
    return max(1, round(len(texto) / 4)) if texto else 0


def contar_caracteres_no_ascii(texto: str) -> int:
    """Cuenta caracteres no ASCII 'significativos' (tildes, ñ, emojis, etc.),

    excluyendo control/formato invisibles. Es un conteo auxiliar, no una
    garantía de conservación del texto.
    """
    return sum(
        1 for c in texto
        if ord(c) > 127 and unicodedata.category(c) not in _CATEGORIAS_CONTROL
    )


def caracteres_especiales_preservados(original: str, limpio: str) -> bool:
    """Compara identidad y orden de Unicode visible, normalizado a NFC.

    Admite la retirada de HTML, scripts, controles y espacios. Conserva los
    unidores de emojis. U+FFFD avisa de una pérdida previa de información.
    Si el original contenía mojibake o pérdida previa de codificación,
    notifica la alerta (False) para trazabilidad.
    """
    visible = _texto_visible(original)
    if "\ufffd" in visible or "\ufffd" in limpio:
        return False

    def secuencia(texto: str) -> list[str]:
        return [
            c for c in unicodedata.normalize("NFC", texto)
            if ord(c) > 127 and not c.isspace()
            and unicodedata.category(c) != "Cc"
            and c not in {"\u200b", "\ufeff"}
        ]

    return secuencia(visible) == secuencia(limpio)
