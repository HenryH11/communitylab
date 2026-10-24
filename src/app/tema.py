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


FUENTES = (
    "@import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@500;600"
    "&family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500"
    "&family=EB+Garamond:wght@400;500&display=swap');"
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
        --cl-tinta-suave: #6e604a;
        --cl-miel: {MIEL};
        --cl-miel-oscura: #8c6214;
        --cl-miel-clara: #f1e2bd;
        --cl-musgo: {MUSGO};
        --cl-noche: #15160f;
        --cl-miel-noche: #d6ab50;
        --cl-titulo: "Cormorant Garamond", Garamond, Georgia, serif;
        --cl-versal: "Cinzel", "Trajan Pro", Georgia, serif;
    }}

    .stApp {{
        background:
            radial-gradient(ellipse 80% 50% at 50% -15%, rgba(214, 171, 80, 0.16), transparent 70%),
            var(--cl-pergamino);
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {{
        color: var(--cl-tinta);
        font-family: var(--cl-titulo);
        font-weight: 600;
        letter-spacing: 0.005em;
    }}
    .stApp h1 {{ font-size: 2.9rem; line-height: 1.1; }}
    .stApp h2 {{ font-size: 2.1rem; }}

    /* Marca: un adelanto nocturno del agente */
    .communitylab-brand {{
        display: flex;
        align-items: center;
        gap: 0.7rem;
        background:
            radial-gradient(ellipse 60% 140% at 0% 50%, rgba(214, 171, 80, 0.14), transparent 70%),
            var(--cl-noche);
        border: 1px solid rgba(214, 171, 80, 0.25);
        border-radius: 0.75rem;
        color: var(--cl-miel-noche);
        font-family: var(--cl-versal);
        font-weight: 600;
        letter-spacing: 0.24em;
        margin-bottom: 1rem;
        padding: 0.75rem 1.1rem;
    }}
    .communitylab-brand .cl-espiral {{ width: 1.45rem; height: 1.45rem; }}

    /* Navegación */
    div[data-testid="stRadio"] > div[role="radiogroup"] {{ gap: 0.4rem; }}
    div[data-testid="stRadio"] label {{
        border-radius: 0.6rem;
        padding: 0.45rem 0.8rem;
        transition: background 0.2s ease;
    }}
    div[data-testid="stRadio"] label:hover {{ background: rgba(176, 125, 34, 0.08); }}
    div[data-testid="stRadio"] label:has(input:checked) {{
        background: var(--cl-miel-clara);
        color: var(--cl-miel-oscura);
        font-weight: 700;
    }}

    button[kind="primary"] {{
        background-color: var(--cl-miel);
        border-color: var(--cl-miel);
        color: #fffaf0;
    }}
    button[kind="primary"]:hover {{
        background-color: var(--cl-miel-oscura);
        border-color: var(--cl-miel-oscura);
        color: #fffaf0;
    }}
    [data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stExpander"] details {{
        background: var(--cl-superficie);
    }}

    .st-key-inicio_card_datos button,
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
