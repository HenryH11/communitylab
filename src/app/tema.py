"""Identidad visual compartida de CommunityLab: paleta "pergamino y miel".

Las páginas generales usan la versión diurna (pergamino claro, tinta sepia y
miel); el agente en vivo usa la versión nocturna de los mismos tonos (ébano,
bosque y miel encendida). Así ambas congenian, pero al entrar al agente la
página resalta por contraste de luz y no por cambio de identidad.
"""

# Espiral de semicírculos crecientes: el logo minimalista de CommunityLab.
_TRAZO_ESPIRAL = (
    "M12 12 a2 2 0 0 1 4 0 a4 4 0 0 1 -8 0 a6 6 0 0 1 12 0 a8 8 0 0 1 -16 0"
)


def espiral(clase: str = "cl-espiral", grosor: float = 1.3) -> str:
    return (
        f'<svg class="{clase}" viewBox="0 1 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="{grosor}" stroke-linecap="round" '
        f'aria-hidden="true"><path pathLength="100" d="{_TRAZO_ESPIRAL}"/></svg>'
    )


# Solo dos pesos por familia: bold para títulos y light para el texto.
FUENTES = (
    "@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@400;700"
    "&family=Cormorant+Garamond:wght@300;700"
    "&family=Inter:wght@300;700&display=swap');"
)

# Colores de gráficas alineados con .streamlit/config.toml.
MIEL = "#b07d22"
MUSGO = "#5b6a42"

ESTILO_GLOBAL = f"""
<style>
    {FUENTES}

    :root {{
        --cl-pergamino: #f5efe1;
        --cl-superficie: #fffaf0;
        --cl-linea: #e3d5b3;
        --cl-tinta: #2b2216;
        --cl-tinta-suave: #54483a;
        --cl-miel: {MIEL};
        --cl-miel-oscura: #8c6214;
        --cl-miel-clara: #f1e2bd;
        --cl-musgo: {MUSGO};
        --cl-noche: #15160f;
        --cl-miel-noche: #d6ab50;
        --cl-titulo: "Cormorant Garamond", Garamond, Georgia, serif;
        --cl-versal: "Cinzel", "Trajan Pro", Georgia, serif;
        --cl-texto: "Inter", "Segoe UI", system-ui, sans-serif;
    }}

    /* Fondo sólido: los degradados translúcidos hacían ver la página borrosa. */
    .stApp {{ background: var(--cl-pergamino); }}
    .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea,
    .stApp td, .stApp th {{
        font-family: var(--cl-texto);
        font-weight: 300;
        -webkit-font-smoothing: antialiased;
    }}
    .stApp strong, .stApp b {{ font-weight: 700; }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        color: var(--cl-tinta);
        font-family: var(--cl-titulo);
        font-weight: 700;
        letter-spacing: 0.005em;
    }}
    .stApp h1 {{ font-size: 3.4rem; line-height: 1.1; }}
    .stApp h2 {{ font-size: 2.3rem; }}

    /* Marca: un adelanto nocturno del agente, con texto blanco y espiral miel */
    .communitylab-brand {{
        display: flex;
        align-items: center;
        gap: 1rem;
        background: var(--cl-noche);
        border-radius: 0.75rem;
        color: #fffaf0;
        font-family: var(--cl-versal);
        font-size: 1.75rem;
        font-weight: 700;
        letter-spacing: 0.2em;
        margin-bottom: 1.2rem;
        padding: 1.1rem 1.6rem;
    }}
    .communitylab-brand .cl-espiral {{
        width: 2.4rem;
        height: 2.4rem;
        color: var(--cl-miel-noche);
    }}

    /* Navegación: la opción activa va en noche con texto blanco, no miel sobre miel */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 0.4rem; }}
    div[data-testid="stRadio"] label {{
        border-radius: 0.6rem;
        padding: 0.5rem 0.9rem;
        transition: background 0.2s ease;
    }}
    div[data-testid="stRadio"] label p {{ font-size: 1.05rem; }}
    div[data-testid="stRadio"] label:hover {{ background: rgba(43, 34, 22, 0.06); }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        background: var(--cl-noche);
    }}
    div[data-testid="stRadio"] label:has(input:checked) p {{
        color: #fffaf0;
        font-weight: 700;
    }}

    button[kind="primary"] {{
        background-color: var(--cl-miel-oscura);
        border-color: var(--cl-miel-oscura);
        color: #fffaf0;
    }}
    button[kind="primary"]:hover {{
        background-color: var(--cl-tinta);
        border-color: var(--cl-tinta);
        color: #fffaf0;
    }}
    [data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stExpander"] details {{
        background: var(--cl-superficie);
    }}
    /* Insignia de inicio: texto blanco sobre noche, no miel sobre miel */
    .st-key-inicio_insignia span {{
        background: var(--cl-noche) !important;
        color: #fffaf0 !important;
        font-weight: 700;
        letter-spacing: 0.08em;
    }}

    .st-key-inicio_card_datos button,
    .st-key-inicio_card_agente button,
    .st-key-inicio_card_analisis button,
    .st-key-inicio_card_an-lisis button,
    .st-key-inicio_card_plantillas button {{
        height: 9rem;
        justify-content: flex-start;
        text-align: left;
        white-space: pre-wrap;
    }}
    .block-container {{
        max-width: 1440px;
        padding-bottom: 2rem;
        padding-top: 3.6rem;
    }}
</style>
"""


def marca() -> str:
    return (
        f'<div class="communitylab-brand">{espiral(grosor=1.6)}'
        "<span>COMMUNITYLAB</span></div>"
    )
