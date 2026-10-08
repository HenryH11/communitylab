from unittest.mock import MagicMock, patch

from src.agentes import reintentos
from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
)
from src.agentes.modelos import (
    SugerenciaPreguntasFrecuentes,
)
from src.agentes.nodos.nodos_generadores import (
    generar_activos,
)

from src.agentes.modelos import (
    CasoDeExito,
    DestaqueBoletin,
    PublicacionLinkedIn,
    SugerenciaPreguntasFrecuentes,
)

def _estado_faq():
    return {
        "id": "fallback-gen-001",
        "autor": "Ana",
        "canal": "#dudas",
        "origen": "Discord",
        "idioma": "es",
        "texto": "¿Cómo conecto un nodo en LangGraph?",
        "tipo_original": "pregunta_tecnica",
        "score_relevancia": 80,
        "elegible_contenido": True,
        "elegible_faq": True,
        "sentimiento": "neutral",
        "tema_principal": "datos_ia",
        "subtema": "conexion de nodos",
        "tipo_detectado": "pregunta_tecnica",
        "rutas": ["preguntas_frecuentes"],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }


def test_generacion_nvidia_falla_y_gemini_respalda(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_GENERACION",
        PROVEEDOR_NVIDIA_NIM,
    )

    generador_nvidia = MagicMock()
    generador_nvidia.invoke.side_effect = TimeoutError(
        "timeout"
    )

    generador_gemini = MagicMock()
    generador_gemini.invoke.return_value = (
        SugerenciaPreguntasFrecuentes(
            tema="LangGraph",
            respuesta="Conecta los nodos mediante edges.",
        )
    )

    def obtener_generadores(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return {
                "preguntas_frecuentes": generador_nvidia
            }

        if proveedor == PROVEEDOR_GEMINI:
            return {
                "preguntas_frecuentes": generador_gemini
            }

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        side_effect=obtener_generadores,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = generar_activos(
            _estado_faq()
        )

    assert resultado["fallos"] == []
    assert resultado["errores"] == []

    assert (
        resultado["activos_generados"]
        ["preguntas_frecuentes"]
        ["tema"]
        == "LangGraph"
    )

    assert generador_nvidia.invoke.call_count == 3
    generador_gemini.invoke.assert_called_once()


def test_generacion_multiruta_fallback_independiente(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_GENERACION",
        PROVEEDOR_NVIDIA_NIM,
    )

    # NVIDIA: caso de éxito funciona
    nvidia_caso = MagicMock()
    nvidia_caso.invoke.return_value = CasoDeExito(
        titular="Ana consigue su primer empleo",
        resumen="Ana consiguió su primer empleo gracias al proyecto.",
    )

    # NVIDIA: boletín falla
    nvidia_boletin = MagicMock()
    nvidia_boletin.invoke.side_effect = TimeoutError(
        "timeout"
    )

    # Gemini: respaldo únicamente para boletín
    gemini_boletin = MagicMock()
    gemini_boletin.invoke.return_value = DestaqueBoletin(
        seccion="Logros",
        titular="Ana consigue su primer empleo",
        resumen="La comunidad celebra el logro profesional de Ana.",
    )

    # NVIDIA: LinkedIn funciona normalmente
    nvidia_linkedin = MagicMock()
    nvidia_linkedin.invoke.return_value = PublicacionLinkedIn(
        titulo="Un nuevo logro profesional",
        contenido="Ana consiguió su primer empleo gracias al proyecto.",
        hashtags=[
            "#Empleabilidad",
            "#AnalistaDeDatos",
            "#Comunidad",
        ],
    )

    # No deberían utilizarse para estas rutas
    gemini_caso = MagicMock()
    gemini_linkedin = MagicMock()

    def obtener_generadores(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return {
                "caso_exito": nvidia_caso,
                "boletin": nvidia_boletin,
                "linkedin": nvidia_linkedin,
            }

        if proveedor == PROVEEDOR_GEMINI:
            return {
                "caso_exito": gemini_caso,
                "boletin": gemini_boletin,
                "linkedin": gemini_linkedin,
            }

        raise AssertionError(proveedor)

    estado = {
        "id": "fallback-multiruta-001",
        "autor": "Ana",
        "canal": "#logros-y-empleos",
        "origen": "Discord",
        "idioma": "es",
        "texto": (
            "Gracias al proyecto conseguí mi primer trabajo "
            "como analista de datos."
        ),
        "tipo_original": "comentario",
        "score_relevancia": 90,
        "elegible_contenido": True,
        "elegible_faq": False,
        "sentimiento": "muy_positivo",
        "tema_principal": "empleabilidad",
        "subtema": "primer empleo",
        "tipo_detectado": "testimonio",
        "rutas": [
            "caso_exito",
            "boletin",
            "linkedin",
        ],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }

    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        side_effect=obtener_generadores,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = generar_activos(
            estado
        )

    assert resultado["errores"] == []
    assert resultado["fallos"] == []

    assert set(
        resultado["activos_generados"]
    ) == {
        "caso_exito",
        "boletin",
        "linkedin",
    }

    # Caso de éxito: NVIDIA directamente
    nvidia_caso.invoke.assert_called_once()
    gemini_caso.invoke.assert_not_called()

    # Boletín: 3 intentos NVIDIA + 1 respaldo Gemini
    assert nvidia_boletin.invoke.call_count == 3
    gemini_boletin.invoke.assert_called_once()

    # LinkedIn: NVIDIA directamente
    nvidia_linkedin.invoke.assert_called_once()
    gemini_linkedin.invoke.assert_not_called()

    assert (
        resultado["activos_generados"]
        ["boletin"]
        ["seccion"]
        == "Logros"
    )

    assert (
        resultado["activos_generados"]
        ["linkedin"]
        ["canal_recomendado"]
        == "LinkedIn Oficial"
    )


def test_fallo_de_ambos_proveedores_no_afecta_otras_rutas(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_GENERACION",
        PROVEEDOR_NVIDIA_NIM,
    )

    nvidia_caso = MagicMock()
    nvidia_caso.invoke.return_value = CasoDeExito(
        titular="Ana consigue su primer empleo",
        resumen="Ana consiguió su primer empleo gracias al proyecto.",
    )

    # Esta ruta fallará con ambos proveedores.
    nvidia_boletin = MagicMock()
    nvidia_boletin.invoke.side_effect = TimeoutError(
        "timeout NVIDIA"
    )

    gemini_boletin = MagicMock()
    gemini_boletin.invoke.side_effect = RuntimeError(
        "fallo Gemini"
    )

    nvidia_linkedin = MagicMock()
    nvidia_linkedin.invoke.return_value = PublicacionLinkedIn(
        titulo="Un nuevo logro profesional",
        contenido="Ana consiguió su primer empleo gracias al proyecto.",
        hashtags=[
            "#Empleabilidad",
            "#AnalistaDeDatos",
            "#Comunidad",
        ],
    )

    gemini_caso = MagicMock()
    gemini_linkedin = MagicMock()

    def obtener_generadores(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return {
                "caso_exito": nvidia_caso,
                "boletin": nvidia_boletin,
                "linkedin": nvidia_linkedin,
            }

        if proveedor == PROVEEDOR_GEMINI:
            return {
                "caso_exito": gemini_caso,
                "boletin": gemini_boletin,
                "linkedin": gemini_linkedin,
            }

        raise AssertionError(proveedor)

    estado = {
        "id": "fallback-doble-fallo-001",
        "autor": "Ana",
        "canal": "#logros-y-empleos",
        "origen": "Discord",
        "idioma": "es",
        "texto": (
            "Gracias al proyecto conseguí mi primer trabajo "
            "como analista de datos."
        ),
        "tipo_original": "comentario",
        "score_relevancia": 90,
        "elegible_contenido": True,
        "elegible_faq": False,
        "sentimiento": "muy_positivo",
        "tema_principal": "empleabilidad",
        "subtema": "primer empleo",
        "tipo_detectado": "testimonio",
        "rutas": [
            "caso_exito",
            "boletin",
            "linkedin",
        ],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }

    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        side_effect=obtener_generadores,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = generar_activos(
            estado
        )

    # Las rutas sanas se conservan.
    assert set(
        resultado["activos_generados"]
    ) == {
        "caso_exito",
        "linkedin",
    }

    assert "boletin" not in resultado["activos_generados"]

    # La ruta fallida hizo retry NIM y luego Gemini.
    assert nvidia_boletin.invoke.call_count == 3
    gemini_boletin.invoke.assert_called_once()

    # Las demás nunca necesitaron Gemini.
    nvidia_caso.invoke.assert_called_once()
    nvidia_linkedin.invoke.assert_called_once()
    gemini_caso.invoke.assert_not_called()
    gemini_linkedin.invoke.assert_not_called()

    # Solo la ruta problemática queda registrada.
    assert len(resultado["fallos"]) == 1
    assert resultado["fallos"][0]["ruta"] == "boletin"
    assert resultado["fallos"][0]["id"] == "fallback-doble-fallo-001"
    
    fallo = resultado["fallos"][0]

    assert fallo["proveedor_primario"] == PROVEEDOR_NVIDIA_NIM
    assert fallo["proveedor_respaldo"] == PROVEEDOR_GEMINI
    assert fallo["fallback_activado"] is True
    assert fallo["motivo_fallback"] == "timeout"

    assert fallo["error_primario"]["tipo"] == "TimeoutError"
    assert fallo["error_respaldo"]["tipo"] == "RuntimeError"

    assert "timeout NVIDIA" not in repr(fallo)
    assert "fallo Gemini" not in repr(fallo)

    assert len(resultado["errores"]) == 1

    # LinkedIn conserva su postprocesamiento normal.
    assert (
        resultado["activos_generados"]
        ["linkedin"]
        ["canal_recomendado"]
        == "LinkedIn Oficial"
    )