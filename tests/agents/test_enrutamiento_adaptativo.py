"""Pruebas unitarias para el enrutamiento adaptativo de modelos de IA."""

from unittest.mock import MagicMock, patch

import pytest

from src.agentes.configuracion_ia import (
    MODELO_NVIDIA_ESTANDAR_POR_DEFECTO,
    MODELO_NVIDIA_RAPIDO_POR_DEFECTO,
    MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO,
    PROVEEDOR_NVIDIA_NIM,
    TIER_ESTANDAR,
    TIER_RAPIDO,
    TIER_RAZONAMIENTO,
    enrutamiento_adaptativo_activo,
    obtener_configuracion_enrutamiento,
    obtener_modelo_nvidia_por_ruta,
    obtener_modelo_nvidia_por_tier,
    obtener_tier_por_ruta,
)
from src.agentes.estado_agente import EstadoAgente
from src.agentes.modelo_ia import obtener_modelo_generacion_estructurado
from src.agentes.modelos import (
    PublicacionLinkedIn,
    SugerenciaPreguntasFrecuentes,
)
from src.agentes.nodos.nodo_enrutador import clasificar_tier_rutas, determinar_rutas

VARIABLES_ENRUTAMIENTO = (
    "COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO",
    "COMMUNITYLAB_MODELO_NVIDIA",
    "COMMUNITYLAB_MODELO_NVIDIA_RAPIDO",
    "COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR",
    "COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO",
)


@pytest.fixture
def sin_env(monkeypatch):
    """Aísla las pruebas de los modelos configurados en el .env local."""
    for variable in VARIABLES_ENRUTAMIENTO:
        monkeypatch.delenv(variable, raising=False)
    with patch("src.agentes.configuracion_ia.load_dotenv"):
        yield


def test_asociacion_de_rutas_a_tiers():
    """Verifica que cada ruta de activo esté mapeada al tier adecuado."""
    assert obtener_tier_por_ruta("preguntas_frecuentes") == TIER_RAPIDO
    assert obtener_tier_por_ruta("boletin") == TIER_RAPIDO
    assert obtener_tier_por_ruta("caso_exito") == TIER_RAZONAMIENTO
    assert obtener_tier_por_ruta("insight_mejora") == TIER_RAZONAMIENTO
    assert obtener_tier_por_ruta("linkedin") == TIER_RAZONAMIENTO
    assert obtener_tier_por_ruta("analisis") == TIER_ESTANDAR
    assert obtener_tier_por_ruta("analisis_lote") == TIER_ESTANDAR
    assert obtener_tier_por_ruta("ruta_desconocida") == TIER_ESTANDAR
    assert obtener_tier_por_ruta(None) == TIER_ESTANDAR


def test_modelos_por_defecto_segun_tier(sin_env):
    """Verifica los modelos predeterminados sin depender del .env."""
    assert (
        obtener_modelo_nvidia_por_tier(TIER_RAPIDO)
        == MODELO_NVIDIA_RAPIDO_POR_DEFECTO
    )
    assert (
        obtener_modelo_nvidia_por_tier(TIER_ESTANDAR)
        == MODELO_NVIDIA_ESTANDAR_POR_DEFECTO
    )
    assert (
        obtener_modelo_nvidia_por_tier(TIER_RAZONAMIENTO)
        == MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO
    )


def test_modelos_por_ruta_segun_tier(sin_env):
    """Verifica la resolución directa de modelo a partir del nombre de ruta."""
    assert (
        obtener_modelo_nvidia_por_ruta("preguntas_frecuentes")
        == MODELO_NVIDIA_RAPIDO_POR_DEFECTO
    )
    assert (
        obtener_modelo_nvidia_por_ruta("caso_exito")
        == MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO
    )
    assert (
        obtener_modelo_nvidia_por_ruta("linkedin")
        == MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO
    )
    assert (
        obtener_modelo_nvidia_por_ruta("boletin")
        == MODELO_NVIDIA_RAPIDO_POR_DEFECTO
    )


def test_configuracion_de_modelos_por_variables_entorno(monkeypatch):
    """Permite sobrescribir los modelos de cada tier mediante variables de entorno."""
    monkeypatch.setenv(
        "COMMUNITYLAB_MODELO_NVIDIA_RAPIDO",
        "mistralai/mistral-7b-instruct-v0.3",
    )
    monkeypatch.setenv(
        "COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO",
        "deepseek-ai/deepseek-r1",
    )
    monkeypatch.setenv(
        "COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR",
        "meta/llama-3.1-70b-instruct",
    )

    with patch("src.agentes.configuracion_ia.load_dotenv", return_value=None):
        assert (
            obtener_modelo_nvidia_por_tier(TIER_RAPIDO)
            == "mistralai/mistral-7b-instruct-v0.3"
        )
        assert (
            obtener_modelo_nvidia_por_tier(TIER_RAZONAMIENTO)
            == "deepseek-ai/deepseek-r1"
        )
        assert (
            obtener_modelo_nvidia_por_tier(TIER_ESTANDAR)
            == "meta/llama-3.1-70b-instruct"
        )


def test_desactivar_enrutamiento_adaptativo_usa_modelo_base(monkeypatch):
    """Si el enrutamiento adaptativo está desactivado, todos los tiers usan el modelo global."""
    monkeypatch.setenv("COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO", "false")
    monkeypatch.setenv("COMMUNITYLAB_MODELO_NVIDIA", "mi-modelo-unico")

    with patch("src.agentes.configuracion_ia.load_dotenv", return_value=None):
        assert not enrutamiento_adaptativo_activo()
        assert obtener_modelo_nvidia_por_tier(TIER_RAPIDO) == "mi-modelo-unico"
        assert (
            obtener_modelo_nvidia_por_tier(TIER_RAZONAMIENTO)
            == "mi-modelo-unico"
        )
        assert (
            obtener_modelo_nvidia_por_ruta("preguntas_frecuentes")
            == "mi-modelo-unico"
        )


def test_clasificar_tier_rutas():
    """Evalúa la precedencia de tiers: si hay rutas complejas, se eleva a razonamiento."""
    assert (
        clasificar_tier_rutas(["caso_exito", "boletin"])
        == TIER_RAZONAMIENTO
    )
    assert clasificar_tier_rutas(["preguntas_frecuentes"]) == TIER_RAPIDO
    assert clasificar_tier_rutas(["boletin"]) == TIER_RAPIDO
    assert clasificar_tier_rutas([]) == TIER_RAPIDO


def test_determinar_rutas_asigna_tier_al_estado():
    """El nodo enrutador añade el campo tier_modelo en la decisión de salida."""
    estado_testimonio: EstadoAgente = {
        "id": "test-1",
        "texto": "Excelente experiencia aprendiendo IA",
        "tipo_detectado": "testimonio",
        "sentimiento": "muy_positivo",
        "score_relevancia": 90,
        "elegible_contenido": True,
        "elegible_faq": False,
    }
    resultado = determinar_rutas(estado_testimonio)
    assert resultado["tier_modelo"] == TIER_RAZONAMIENTO
    assert "caso_exito" in resultado["rutas"]

    estado_faq: EstadoAgente = {
        "id": "test-2",
        "texto": "¿Cómo configuro las variables de entorno?",
        "tipo_detectado": "pregunta_tecnica",
        "sentimiento": "neutral",
        "score_relevancia": 75,
        "elegible_contenido": True,
        "elegible_faq": True,
    }
    resultado_faq = determinar_rutas(estado_faq)
    assert resultado_faq["tier_modelo"] == TIER_RAPIDO
    assert resultado_faq["rutas"] == ["preguntas_frecuentes"]


def test_fachada_generacion_resuelve_modelo_adaptativo_segun_ruta(sin_env):
    """La fachada selecciona automáticamente el modelo del tier adecuado para cada ruta."""
    modelo_mock = MagicMock()

    with patch(
        "src.agentes.modelo_ia.obtener_modelo_nvidia_estructurado",
        return_value=modelo_mock,
    ) as obtener_nvidia:
        obtener_modelo_generacion_estructurado(
            SugerenciaPreguntasFrecuentes,
            proveedor=PROVEEDOR_NVIDIA_NIM,
            ruta="preguntas_frecuentes",
        )
        obtener_nvidia.assert_called_once_with(
            SugerenciaPreguntasFrecuentes,
            modelo=MODELO_NVIDIA_RAPIDO_POR_DEFECTO,
        )

    with patch(
        "src.agentes.modelo_ia.obtener_modelo_nvidia_estructurado",
        return_value=modelo_mock,
    ) as obtener_nvidia:
        obtener_modelo_generacion_estructurado(
            PublicacionLinkedIn,
            proveedor=PROVEEDOR_NVIDIA_NIM,
            ruta="linkedin",
        )
        obtener_nvidia.assert_called_once_with(
            PublicacionLinkedIn,
            modelo=MODELO_NVIDIA_RAZONAMIENTO_POR_DEFECTO,
        )


def test_obtener_configuracion_enrutamiento(sin_env):
    """Valida el reporte estructurado de configuración no secreta de tiers."""
    config = obtener_configuracion_enrutamiento()
    assert config["enrutamiento_adaptativo_activo"] is True
    assert TIER_RAPIDO in config["tiers"]
    assert TIER_ESTANDAR in config["tiers"]
    assert TIER_RAZONAMIENTO in config["tiers"]
    assert "preguntas_frecuentes" in config["tiers"][TIER_RAPIDO]["rutas"]
    assert "caso_exito" in config["tiers"][TIER_RAZONAMIENTO]["rutas"]
