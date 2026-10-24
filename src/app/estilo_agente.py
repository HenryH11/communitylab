"""Tema visual gótico formal del agente en vivo.

Es la versión nocturna de la paleta "pergamino y miel" de `tema.py`: ébano,
bosque, nogal y miel encendida con tipografía serif clásica (naturaleza, fauna
y madera en clave sobria). Comparte tonos con el resto de la app, pero resalta
por contraste de luz. Los estilos solo se inyectan al renderizar esa vista.
"""

from html import escape

from src.app.tema import espiral

NOMBRES_PLATAFORMA = {"linkedin": "LinkedIn", "instagram": "Instagram", "x": "X"}

EMBLEMA = espiral("gotico-emblema", grosor=1.2)

ESTILO = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600&family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=EB+Garamond:wght@400;500&display=swap');

    :root {
        --ebano: #0c0b08;
        --noche: #15140e;
        --bosque: #1d1d14;
        --musgo: #2f2e1e;
        --laton: #d4a84c;
        --laton-tenue: rgba(212, 168, 76, 0.35);
        --marfil: #f3e9cc;
        --salvia: #aca37f;
        --nogal: #271c10;
        --serif-titulo: "Cinzel", "Trajan Pro", Georgia, serif;
        --serif-display: "Cormorant Garamond", Garamond, Georgia, serif;
        --serif-texto: "EB Garamond", Garamond, Georgia, serif;
        --veta: repeating-linear-gradient(
            90deg,
            rgba(255, 235, 200, 0.018) 0 1px,
            transparent 1px 7px,
            rgba(0, 0, 0, 0.05) 7px 8px,
            transparent 8px 19px
        );
    }

    .stApp {
        background:
            radial-gradient(ellipse 70% 45% at 50% -10%, rgba(214, 168, 76, 0.13), transparent 70%),
            radial-gradient(ellipse 100% 70% at 50% 120%, rgba(0, 0, 0, 0.7), transparent 70%),
            linear-gradient(180deg, var(--noche), var(--ebano));
        color: var(--marfil);
    }
    header[data-testid="stHeader"] { background: transparent; }
    header[data-testid="stHeader"] * { color: var(--salvia); }

    /* Barra de marca y navegación en clave sobria */
    .communitylab-brand {
        background: transparent !important;
        border: 1px solid var(--laton-tenue);
        color: var(--laton) !important;
        font-family: var(--serif-titulo);
        letter-spacing: 0.22em !important;
    }
    div[data-testid="stRadio"] label p { color: var(--salvia); font-family: var(--serif-texto); }
    div[data-testid="stRadio"] label > div > div:first-child:not([data-testid]) { display: none; }
    div[data-testid="stRadio"] label:has(input:checked) {
        background: transparent;
        box-shadow: inset 0 -1px 0 var(--laton);
        border-radius: 0;
    }
    div[data-testid="stRadio"] label:has(input:checked) p { color: var(--marfil); }

    /* Lienzo central, como un chat de LLM */
    .st-key-gotico_lienzo {
        max-width: 780px;
        margin: 0 auto;
        padding-bottom: 7rem;
    }
    .st-key-gotico_lienzo p,
    .st-key-gotico_lienzo li,
    .st-key-gotico_lienzo label {
        font-family: var(--serif-texto);
        color: var(--marfil);
    }

    .gotico-cabecera {
        text-align: center;
        margin: 9vh 0 2rem;
        animation: gotico-aparecer 0.8s ease-out both;
    }
    .gotico-emblema { width: 54px; height: 54px; color: var(--laton); }
    .gotico-cabecera .gotico-emblema path {
        stroke-dasharray: 100;
        animation: gotico-trazar 2.4s cubic-bezier(.6, 0, .3, 1) both;
    }
    .gotico-cabecera p.gotico-titulo {
        margin: 0.7rem 0 0.1rem;
        font-family: var(--serif-titulo);
        font-weight: 500;
        font-size: 0.95rem;
        letter-spacing: 0.32em;
        color: var(--laton);
    }
    .gotico-cabecera p.gotico-lema {
        margin: 0;
        font-family: var(--serif-display);
        font-style: italic;
        font-size: 2.3rem;
        line-height: 1.25;
        color: var(--marfil);
    }
    .gotico-ornamento {
        display: flex;
        align-items: center;
        gap: 0.9rem;
        margin: 1rem auto 0;
        max-width: 320px;
        color: var(--laton);
        font-size: 1rem;
    }
    .gotico-ornamento::before,
    .gotico-ornamento::after {
        content: "";
        flex: 1;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--laton-tenue), transparent);
    }

    /* Barra de estado: madera de nogal con filete de latón */
    .st-key-gotico_barra {
        padding: 0.55rem 1rem;
        margin-bottom: 1.6rem;
        border: 1px solid var(--laton-tenue);
        border-radius: 4px;
        background: var(--veta), linear-gradient(180deg, #1f160c, var(--nogal));
    }
    .gotico-estado {
        font-family: var(--serif-titulo);
        font-size: 0.72rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--salvia);
        padding-top: 0.35rem;
    }
    .gotico-estado b { color: var(--laton); font-weight: 600; }
    .st-key-gotico_barra [data-testid="stCheckbox"] label p {
        font-family: var(--serif-titulo) !important;
        font-size: 0.72rem !important;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: var(--salvia) !important;
    }
    /* La pista del interruptor es el primer div sin testid de la etiqueta. */
    .st-key-gotico_barra [data-testid="stCheckbox"] label > div:not([data-testid]) {
        background: rgba(212, 168, 76, 0.22) !important;
    }
    .st-key-gotico_barra [data-testid="stCheckbox"] label:has(input:checked) > div:not([data-testid]) {
        background: var(--laton) !important;
    }
    .st-key-gotico_barra [data-testid="stCheckbox"] label > div:not([data-testid]) > div {
        background: var(--marfil) !important;
    }

    /* Mensajes */
    [data-testid="stChatMessage"] {
        background: transparent;
        padding: 0.4rem 0;
        margin-bottom: 1.1rem;
        animation: gotico-aparecer 0.5s ease-out both;
    }
    [data-testid="stChatMessage"] > [data-testid^="stChatMessageAvatar"],
    [data-testid="stChatMessage"] > div:first-child:not([data-testid="stChatMessageContent"]) {
        display: none;
    }
    [data-testid="stChatMessage"]:has(.gotico-voz-persona) {
        width: fit-content;
        max-width: 78%;
        margin-left: auto;
        padding: 0.75rem 1.1rem;
        border: 1px solid var(--laton-tenue);
        border-radius: 14px 14px 2px 14px;
        background: var(--veta), linear-gradient(180deg, #241a0f, #1a130b);
    }
    [data-testid="stChatMessage"] [data-testid="stElementContainer"]:has(.gotico-voz-persona) {
        display: none;
    }
    [data-testid="stChatMessage"]:has(.gotico-voz-agente) p,
    [data-testid="stChatMessage"]:has(.gotico-voz-agente) li {
        font-size: 1.08rem;
        line-height: 1.7;
    }
    [data-testid="stChatMessage"] strong { color: #fbf1d3; }
    .gotico-firma {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-family: var(--serif-titulo);
        font-size: 0.7rem;
        letter-spacing: 0.24em;
        color: var(--laton);
    }
    .gotico-firma .gotico-emblema { width: 17px; height: 17px; }
    [data-testid="stChatMessage"]:has(.gotico-voz-agente) [data-testid="stMarkdownContainer"] .gotico-firma {
        margin-bottom: 0.25rem;
    }

    /* Borrador: folio con doble filete */
    .gotico-borrador {
        margin: 0.9rem 0 0.3rem;
        padding: 1.3rem 1.5rem 1.1rem;
        border: 1px solid var(--laton-tenue);
        outline: 1px solid rgba(212, 168, 76, 0.15);
        outline-offset: 4px;
        border-radius: 2px;
        background: linear-gradient(180deg, rgba(47, 46, 30, 0.4), rgba(21, 20, 14, 0.65));
    }
    .gotico-borrador-plataforma {
        font-family: var(--serif-titulo);
        font-size: 0.68rem;
        letter-spacing: 0.26em;
        text-transform: uppercase;
        color: var(--laton);
    }
    .gotico-borrador-titulo {
        margin: 0.35rem 0 0.7rem;
        font-family: var(--serif-display);
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--marfil);
    }
    .gotico-borrador-contenido {
        font-family: var(--serif-texto);
        font-size: 1.02rem;
        line-height: 1.7;
        color: var(--marfil);
    }
    .gotico-hashtags {
        margin-top: 0.9rem;
        padding-top: 0.6rem;
        border-top: 1px solid rgba(212, 168, 76, 0.18);
        font-family: var(--serif-texto);
        font-style: italic;
        color: var(--salvia);
    }

    /* Desplegables de fuentes y verificación */
    .st-key-gotico_lienzo [data-testid="stExpander"] details {
        background: transparent;
        border: none;
        border-top: 1px solid rgba(212, 168, 76, 0.18);
        border-radius: 0;
    }
    .st-key-gotico_lienzo [data-testid="stExpander"] summary p {
        font-family: var(--serif-titulo);
        font-size: 0.7rem;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: var(--laton);
    }
    .st-key-gotico_lienzo [data-testid="stCaptionContainer"],
    .st-key-gotico_lienzo [data-testid="stCaptionContainer"] p { color: var(--salvia); }

    /* Entrada fija al pie, como en un chat de LLM */
    [data-testid="stBottom"] > div {
        background: linear-gradient(180deg, transparent, var(--ebano) 35%);
    }
    [data-testid="stBottomBlockContainer"] {
        max-width: 812px;
        padding-bottom: 1.6rem;
    }
    [data-testid="stChatInput"] {
        background: #17160f;
        border: 1px solid var(--laton-tenue) !important;
        border-radius: 14px;
        transition: border-color 0.3s ease, box-shadow 0.3s ease;
    }
    [data-testid="stChatInput"]:focus-within {
        border-color: var(--laton) !important;
        box-shadow: 0 0 0 1px rgba(212, 168, 76, 0.25), 0 12px 40px rgba(0, 0, 0, 0.55);
    }
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] > div:focus-within {
        background: transparent;
        border-color: transparent !important;
    }
    [data-testid="stChatInput"] textarea {
        font-family: var(--serif-texto);
        font-size: 1.05rem;
        color: var(--marfil);
        caret-color: var(--laton);
    }
    [data-testid="stChatInput"] textarea::placeholder { color: #81775a; font-style: italic; }
    [data-testid="stChatInput"] button {
        background: transparent;
        border: 1px solid var(--laton-tenue);
        color: var(--laton);
    }

    [data-testid="stSpinner"] p { font-family: var(--serif-display); font-style: italic; color: var(--salvia); }

    @keyframes gotico-trazar {
        from { stroke-dashoffset: 100; }
        to { stroke-dashoffset: 0; }
    }
    @keyframes gotico-aparecer {
        from { opacity: 0; transform: translateY(6px); }
        to { opacity: 1; transform: none; }
    }
    @media (prefers-reduced-motion: reduce) {
        .gotico-cabecera, [data-testid="stChatMessage"],
        .gotico-cabecera .gotico-emblema path { animation: none; }
    }
</style>
"""


def cabecera(lema: str) -> str:
    return (
        '<div class="gotico-cabecera">'
        f"{EMBLEMA}"
        '<p class="gotico-titulo">AGENTE COMMUNITYLAB</p>'
        f'<p class="gotico-lema">{escape(lema)}</p>'
        '<div class="gotico-ornamento">❧</div>'
        "</div>"
    )


def estado(total: int, con_activos: int) -> str:
    return (
        '<div class="gotico-estado">Lote procesado · '
        f"<b>{total}</b> mensajes · <b>{con_activos}</b> con activos</div>"
    )


def marca_voz(rol: str) -> str:
    """Marca que da a cada mensaje su estilo según quién habla."""
    if rol == "user":
        return '<span class="gotico-voz-persona"></span>'
    return (
        '<div class="gotico-firma gotico-voz-agente">'
        f"{EMBLEMA}<span>COMMUNITYLAB</span></div>"
    )


def borrador(datos: dict) -> str:
    plataforma = NOMBRES_PLATAFORMA.get(datos.get("plataforma", ""), "Borrador")
    contenido = escape(datos.get("contenido", "")).replace("\n", "<br>")
    hashtags = " · ".join(escape(etiqueta) for etiqueta in datos.get("hashtags", []))
    return (
        '<div class="gotico-borrador">'
        f'<div class="gotico-borrador-plataforma">Borrador · {escape(plataforma)}</div>'
        f'<div class="gotico-borrador-titulo">{escape(datos.get("titulo", ""))}</div>'
        f'<div class="gotico-borrador-contenido">{contenido}</div>'
        f'<div class="gotico-hashtags">{hashtags}</div>'
        "</div>"
    )
