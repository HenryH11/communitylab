"""Configuración no secreta de proveedores y modelos de IA."""

import os
from typing import TypedDict

from dotenv import load_dotenv
from src.agentes.errores_ia import ErrorConfiguracionProveedor

PROVEEDOR_GEMINI = "gemini"
PROVEEDOR_NVIDIA_NIM = "nvidia_nim"

PROVEEDORES_SOPORTADOS = {
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
}

VARIABLE_PROVEEDOR_ANALISIS = "COMMUNITYLAB_PROVEEDOR_ANALISIS"

VARIABLE_PROVEEDOR_GENERACION = ("COMMUNITYLAB_PROVEEDOR_GENERACION")

VARIABLE_MODELO_GEMINI = "COMMUNITYLAB_MODELO_GEMINI"


VARIABLE_MODELO_NVIDIA = "COMMUNITYLAB_MODELO_NVIDIA"
VARIABLE_MODELO_NVIDIA_INTERPRETACION = "COMMUNITYLAB_MODELO_NVIDIA_INTERPRETACION"

VARIABLE_TIMEOUT_NVIDIA = "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS"

TIMEOUT_NVIDIA_POR_DEFECTO = 15.0

PROVEEDOR_GENERACION_POR_DEFECTO = PROVEEDOR_NVIDIA_NIM

PROVEEDOR_ANALISIS_POR_DEFECTO = PROVEEDOR_NVIDIA_NIM


NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# =============================================================
# CATALOGO DE MODELOS DE IA : VALORES PREDETERMINADOS
# =============================================================
# Las variables de entorno tienen prioridad sobre estos valores.

# Gemini: proveedor principal o respaldo.
MODELO_GEMINI_POR_DEFECTO = "gemini-3.5-flash-lite"

# NVIDIA global: utilizado sin enrutamiento adaptativo.
MODELO_NVIDIA_POR_DEFECTO = "nvidia/nemotron-3.5-lightning-30b-a3b"

# Generacion rapida: FAQ y boletines.
MODELO_NVIDIA_RAPIDO_POR_DEFECTO = MODELO_NVIDIA_POR_DEFECTO

# Analisis de mensajes: individual y por lotes.
MODELO_NVIDIA_ESTANDAR_POR_DEFECTO = "nvidia/nemotron-3.5-super-vl-120b-a12b"

# Generacion elaborada: LinkedIn, casos de exito e insights.
MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO = "nvidia/nemotron-3.5-super-vl-120b-a12b"

# Alias historico conservado por compatibilidad.
MODELO_NVIDIA_NEMOTRON = MODELO_NVIDIA_POR_DEFECTO


# Modelo NVIDIA NIM configurado por defecto para el tier estándar.


# Los reintentos los controla la capa de aplicación.
# Evitamos sumar retries ocultos del cliente NVIDIA.
MAX_RETRIES_CLIENTE_NVIDIA = 0

# -------------------------------------------------------------
# Tiers y Enrutamiento Adaptativo de Modelos
# -------------------------------------------------------------
TIER_RAPIDO = "rapido"
TIER_ESTANDAR = "estandar"
TIER_RAZONAMIENTO = "razonamiento"

TIERS_SOPORTADOS = {
    TIER_RAPIDO,
    TIER_ESTANDAR,
    TIER_RAZONAMIENTO,
}

VARIABLE_ENRUTAMIENTO_ADAPTATIVO = "COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO"
VARIABLE_MODELO_NVIDIA_RAPIDO = "COMMUNITYLAB_MODELO_NVIDIA_RAPIDO"
VARIABLE_MODELO_NVIDIA_ESTANDAR = "COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR"
VARIABLE_MODELO_NVIDIA_RAZONAMIENTO = "COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO"



# Mapeo de rutas de generación y etapas a sus correspondientes tiers
MAPEO_RUTAS_A_TIERS: dict[str, str] = {
    "preguntas_frecuentes": TIER_RAPIDO,
    "boletin": TIER_RAPIDO,
    "caso_exito": TIER_RAZONAMIENTO,
    "insight_mejora": TIER_RAZONAMIENTO,
    "linkedin": TIER_RAZONAMIENTO,
    "analisis": TIER_ESTANDAR,
    "analisis_lote": TIER_ESTANDAR,
}


def enrutamiento_adaptativo_activo() -> bool:
    """Indica si el enrutamiento adaptativo de modelos por tier está activado."""
    load_dotenv()
    valor = os.getenv(VARIABLE_ENRUTAMIENTO_ADAPTATIVO, "true").strip().lower()
    return valor not in {"false", "0", "no", "off"}


def obtener_tier_por_ruta(ruta: str | None) -> str:
    """Devuelve el tier asociado a una ruta de generación o etapa."""
    if not ruta:
        return TIER_ESTANDAR
    return MAPEO_RUTAS_A_TIERS.get(ruta, TIER_ESTANDAR)


def obtener_modelo_nvidia_por_tier(tier: str) -> str:
    """Obtiene el identificador de modelo NVIDIA NIM configurado para un tier."""
    load_dotenv()
    if not enrutamiento_adaptativo_activo():
        return obtener_modelo_nvidia_id()

    if tier == TIER_RAPIDO:
        return (
            os.getenv(
                VARIABLE_MODELO_NVIDIA_RAPIDO,
                MODELO_NVIDIA_RAPIDO_POR_DEFECTO,
            ).strip()
            or MODELO_NVIDIA_RAPIDO_POR_DEFECTO
        )

    if tier == TIER_RAZONAMIENTO:
        return (
            os.getenv(
                VARIABLE_MODELO_NVIDIA_RAZONAMIENTO,
                MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO,
            ).strip()
            or MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO
        )

    return (
        os.getenv(
            VARIABLE_MODELO_NVIDIA_ESTANDAR,
            MODELO_NVIDIA_ESTANDAR_POR_DEFECTO,
        ).strip()
        or MODELO_NVIDIA_ESTANDAR_POR_DEFECTO
    )


def obtener_modelo_nvidia_por_ruta(ruta: str | None) -> str:
    """Obtiene el modelo de NVIDIA NIM correspondiente a la ruta según su tier."""
    tier = obtener_tier_por_ruta(ruta)
    return obtener_modelo_nvidia_por_tier(tier)


def obtener_modelo_nvidia_interpretacion() -> str:
    """El intérprete usa Super por defecto, independiente del modelo redactor."""
    load_dotenv()
    return (
        os.getenv(
            VARIABLE_MODELO_NVIDIA_INTERPRETACION, MODELO_NVIDIA_ESTANDAR_POR_DEFECTO
        ).strip()
        or MODELO_NVIDIA_ESTANDAR_POR_DEFECTO
    )


class ConfiguracionTier(TypedDict):
    modelo_nvidia: str
    rutas: list[str]


class ConfiguracionEnrutamiento(TypedDict):
    enrutamiento_adaptativo_activo: bool
    tiers: dict[str, ConfiguracionTier]


def obtener_configuracion_enrutamiento() -> ConfiguracionEnrutamiento:
    """Devuelve la configuración no secreta del enrutamiento adaptativo."""
    return {
        "enrutamiento_adaptativo_activo": enrutamiento_adaptativo_activo(),
        "tiers": {
            TIER_RAPIDO: {
                "modelo_nvidia": obtener_modelo_nvidia_por_tier(TIER_RAPIDO),
                "rutas": ["preguntas_frecuentes", "boletin"],
            },
            TIER_ESTANDAR: {
                "modelo_nvidia": obtener_modelo_nvidia_por_tier(TIER_ESTANDAR),
                "rutas": ["analisis", "analisis_lote"],
            },
            TIER_RAZONAMIENTO: {
                "modelo_nvidia": obtener_modelo_nvidia_por_tier(TIER_RAZONAMIENTO),
                "rutas": ["caso_exito", "insight_mejora", "linkedin"],
            },
        },
    }


def obtener_modelo_gemini_id() -> str:
    """Obtiene el modelo Gemini configurado."""
    load_dotenv()
    return (
        os.getenv(VARIABLE_MODELO_GEMINI, MODELO_GEMINI_POR_DEFECTO).strip()
        or MODELO_GEMINI_POR_DEFECTO
    )


def obtener_modelo_nvidia_id() -> str:
    """Obtiene y valida el identificador de modelo configurado para NVIDIA NIM."""
    load_dotenv()

    modelo = os.getenv(
        VARIABLE_MODELO_NVIDIA,
        MODELO_NVIDIA_POR_DEFECTO,
    ).strip()

    if not modelo:
        return MODELO_NVIDIA_POR_DEFECTO

    return modelo


def obtener_proveedor_analisis() -> str:
    """Obtiene y valida el proveedor configurado para análisis."""
    load_dotenv()

    proveedor = os.getenv(
        VARIABLE_PROVEEDOR_ANALISIS,
        PROVEEDOR_ANALISIS_POR_DEFECTO,
    ).strip().lower()

    if proveedor not in PROVEEDORES_SOPORTADOS:
        opciones = ", ".join(
            sorted(PROVEEDORES_SOPORTADOS)
        )
        raise ValueError(
            f"Proveedor de análisis no soportado: {proveedor}. "
            f"Opciones válidas: {opciones}."
        )

    return proveedor


def obtener_proveedor_generacion() -> str:
    """Obtiene y valida el proveedor configurado para generación."""
    load_dotenv()

    proveedor = os.getenv(
        VARIABLE_PROVEEDOR_GENERACION,
        PROVEEDOR_GENERACION_POR_DEFECTO,
    ).strip().lower()

    if proveedor not in PROVEEDORES_SOPORTADOS:
        opciones = ", ".join(
            sorted(PROVEEDORES_SOPORTADOS)
        )
        raise ValueError(
            f"Proveedor de generación no soportado: {proveedor}. "
            f"Opciones válidas: {opciones}."
        )

    return proveedor


# Reintentos de la capa de aplicacion (no del cliente LLM).
VARIABLE_MAX_INTENTOS_IA = "COMMUNITYLAB_MAX_INTENTOS_IA"
MAX_INTENTOS_IA_POR_DEFECTO = 3


def obtener_max_intentos_ia() -> int:
    load_dotenv()
    valor = os.getenv(
        VARIABLE_MAX_INTENTOS_IA,
        str(MAX_INTENTOS_IA_POR_DEFECTO),
    ).strip()

    try:
        intentos = int(valor)
    except ValueError as error:
        raise ErrorConfiguracionProveedor(
            f"{VARIABLE_MAX_INTENTOS_IA} debe ser un entero."
        ) from error

    if intentos < 1:
        raise ErrorConfiguracionProveedor(
            f"{VARIABLE_MAX_INTENTOS_IA} debe ser mayor que cero."
        )

    return intentos


# Esperas entre reintentos de la capa de aplicacion.
VARIABLE_ESPERA_BASE_IA = "COMMUNITYLAB_ESPERA_BASE_IA_SEGUNDOS"
VARIABLE_ESPERA_MAXIMA_IA = "COMMUNITYLAB_ESPERA_MAXIMA_IA_SEGUNDOS"

ESPERA_BASE_IA_POR_DEFECTO = 2.0
ESPERA_MAXIMA_IA_POR_DEFECTO = 30.0


def obtener_esperas_reintentos_ia() -> tuple[float, float]:
    """Obtiene y valida las esperas base y maxima."""
    load_dotenv()

    try:
        base = float(os.getenv(
            VARIABLE_ESPERA_BASE_IA,
            str(ESPERA_BASE_IA_POR_DEFECTO),
        ))
        maxima = float(os.getenv(
            VARIABLE_ESPERA_MAXIMA_IA,
            str(ESPERA_MAXIMA_IA_POR_DEFECTO),
        ))
    except ValueError as error:
        raise ErrorConfiguracionProveedor(
            "Las esperas de IA deben ser numeros."
        ) from error

    if not (
        0 < base < float("inf")
        and base <= maxima < float("inf")
    ):
        raise ErrorConfiguracionProveedor(
            "Las esperas deben ser positivas y la maxima "
            "no puede ser menor que la base."
        )

    return base, maxima


# Recuperacion posterior al procesamiento.
VARIABLE_PASADAS_RECUPERACION = "COMMUNITYLAB_PASADAS_RECUPERACION"
PASADAS_RECUPERACION_POR_DEFECTO = 1


def obtener_pasadas_recuperacion() -> int:
    # Numero de pasadas adicionales sobre resultados fallidos.
    load_dotenv()
    valor = os.getenv(
        VARIABLE_PASADAS_RECUPERACION,
        str(PASADAS_RECUPERACION_POR_DEFECTO),
    ).strip()

    try:
        pasadas = int(valor)
    except ValueError as error:
        raise ErrorConfiguracionProveedor(
            "Las pasadas de recuperacion deben ser un entero."
        ) from error

    if not 0 <= pasadas <= 3:
        raise ErrorConfiguracionProveedor(
            "Las pasadas de recuperacion deben estar entre 0 y 3."
        )

    return pasadas


# Concurrencia experimental de Data Science.
VARIABLE_CONCURRENCIA_MENSAJES = "COMMUNITYLAB_CONCURRENCIA_MENSAJES"
VARIABLE_CONCURRENCIA_LOTES_ANALISIS = "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS"

CONCURRENCIA_POR_DEFECTO = 1
CONCURRENCIA_MAXIMA_EXPERIMENTAL = 2


def _obtener_concurrencia_experimental(variable: str) -> int:
    valor = os.getenv(variable, str(CONCURRENCIA_POR_DEFECTO)).strip()

    try:
        concurrencia = int(valor)
    except ValueError as error:
        raise ValueError(f"{variable} debe ser 1 o 2") from error

    if not 1 <= concurrencia <= CONCURRENCIA_MAXIMA_EXPERIMENTAL:
        raise ValueError(f"{variable} debe ser 1 o 2")

    return concurrencia


def obtener_concurrencia_mensajes() -> int:
    return _obtener_concurrencia_experimental(
        VARIABLE_CONCURRENCIA_MENSAJES
    )


def obtener_concurrencia_lotes_analisis() -> int:
    return _obtener_concurrencia_experimental(
        VARIABLE_CONCURRENCIA_LOTES_ANALISIS
    )


def obtener_timeout_nvidia() -> float:
    """Obtiene y valida el timeout configurable de NVIDIA NIM."""
    load_dotenv()

    valor = os.getenv(
        VARIABLE_TIMEOUT_NVIDIA,
        str(TIMEOUT_NVIDIA_POR_DEFECTO),
    ).strip()

    try:
        timeout = float(valor)
    except ValueError as error:
        raise ErrorConfiguracionProveedor(
            f"{VARIABLE_TIMEOUT_NVIDIA} debe ser un número."
        ) from error

    if timeout <= 0:
        raise ErrorConfiguracionProveedor(
            f"{VARIABLE_TIMEOUT_NVIDIA} debe ser mayor que cero."
        )

    return timeout