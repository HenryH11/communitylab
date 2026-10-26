import logging

from unittest.mock import MagicMock, patch

from src.agentes.estado_agente import EstadoAgente
from src.agentes.recuperacion import ids_reintentables

from src.agentes.errores_ia import ErrorSalidaProveedor

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
)
from src.agentes.modelos import AnalisisMensaje
from src.agentes import reintentos
from src.agentes.nodos.nodo_analizador import analizar_mensaje


def _estado() -> EstadoAgente:
    return {
        "id": "fallback-001",
        "autor": "Ana",
        "canal": "#dudas",
        "origen": "Discord",
        "idioma": "es",
        "texto": "¿Cómo conecto un nodo en LangGraph?",
        "tipo_original": "pregunta_tecnica",
        "score_relevancia": 80,
        "elegible_contenido": True,
        "elegible_faq": True,
        "rutas": [],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
    }


def test_analisis_nvidia_falla_y_gemini_respalda(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = TimeoutError(
        "timeout"
    )

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="conexion de nodos",
        tipo_detectado="pregunta_tecnica",
        es_spam_detectado=False,
        motivo_spam=None,
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado["sentimiento"] == "neutral"
    assert resultado["tipo_detectado"] == "pregunta_tecnica"

    assert cadena_nvidia.invoke.call_count == 3
    cadena_gemini.invoke.assert_called_once()

    assert resultado.get("errores", []) == []
    assert resultado.get("fallos", []) == []


def test_analisis_nvidia_salida_invalida_y_gemini_respalda(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = ErrorSalidaProveedor(
        "salida inválida"
    )

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="conexion de nodos",
        tipo_detectado="pregunta_tecnica",
        es_spam_detectado=False,
        motivo_spam=None,
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado["sentimiento"] == "neutral"
    assert resultado["tema_principal"] == "datos_ia"
    assert resultado["tipo_detectado"] == "pregunta_tecnica"

    assert cadena_nvidia.invoke.call_count == 3
    cadena_gemini.invoke.assert_called_once()

    assert resultado.get("errores", []) == []
    assert resultado.get("fallos", []) == []


def test_doble_fallo_analisis_transitorio_se_marca_para_recuperacion(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = TimeoutError(
        "timeout NVIDIA"
    )

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.side_effect = ConnectionError(
        "conexion Gemini"
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert len(resultado["fallos"]) == 1

    fallo = resultado["fallos"][0]

    assert fallo["reintentable"] is True
    assert fallo["fallback_activado"] is True
    assert fallo["proveedor_primario"] == PROVEEDOR_NVIDIA_NIM
    assert fallo["proveedor_respaldo"] == PROVEEDOR_GEMINI

    estado_resultado = {
        **_estado(),
        **resultado,
    }

    assert ids_reintentables(
        [estado_resultado]
    ) == ["fallback-001"]

    assert cadena_nvidia.invoke.call_count == 3
    cadena_gemini.invoke.assert_called_once()


def test_retry_interno_nvidia_conserva_id_analisis(
    monkeypatch,
    caplog,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = TimeoutError(
        "timeout NVIDIA"
    )

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="conexion de nodos",
        tipo_detectado="pregunta_tecnica",
        es_spam_detectado=False,
        motivo_spam=None,
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with caplog.at_level(
        logging.WARNING,
        logger="communitylab.ciencia_datos",
    ), patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ), patch.object(
        reintentos,
        "_esperar",
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado.get("fallos", []) == []

    eventos = [
        registro
        for registro in caplog.records
        if getattr(
            registro,
            "evento",
            None,
        ) == "reintento_programado"
    ]

    assert len(eventos) == 2

    for registro in eventos:
        campos = registro.campos

        assert campos["id_interaccion"] == "fallback-001"
        assert campos["etapa"] == "proveedor_primario"
        assert campos["proveedor"] == PROVEEDOR_NVIDIA_NIM
        assert "ruta" not in campos

    assert [
        registro.campos["intento"]
        for registro in eventos
    ] == [1, 2]


class _ErrorNvidiaDegraded(Exception):
    def __init__(self):
        super().__init__(
            "Error code: 400 - "
            "{'status': 400, 'title': 'Bad Request', "
            "'detail': 'Function id: DEGRADED function cannot be invoked'}"
        )
        self.status_code = 400


def test_analisis_nvidia_error_400_degraded_activa_fallback_gemini(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = _ErrorNvidiaDegraded()

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="fallback degradado",
        tipo_detectado="pregunta_tecnica",
        es_spam_detectado=False,
        motivo_spam=None,
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado.get("fallos", []) == []
    cadena_nvidia.invoke.assert_called_once()
    cadena_gemini.invoke.assert_called_once()


class _Error400Normal(Exception):
    def __init__(self):
        super().__init__("Bad Request")
        self.status_code = 400


class _ErrorNvidiaGoneAnalisis(Exception):
    def __init__(self):
        super().__init__(
            "Error code: 410 - "
            "{'status': 410, 'title': 'Gone', "
            "'detail': 'The model is no longer available'}"
        )
        self.status_code = 410


def test_analisis_nvidia_error_410_activa_fallback_gemini(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = _ErrorNvidiaGoneAnalisis()

    cadena_gemini = MagicMock()
    cadena_gemini.invoke.return_value = AnalisisMensaje(
        sentimiento="neutral",
        tema_principal="datos_ia",
        subtema="fallback modelo retirado",
        tipo_detectado="pregunta_tecnica",
        es_spam_detectado=False,
        motivo_spam=None,
    )

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert resultado.get("fallos", []) == []
    cadena_nvidia.invoke.assert_called_once()
    cadena_gemini.invoke.assert_called_once()


def test_analisis_nvidia_error_400_normal_no_activa_fallback_gemini(
    monkeypatch,
):
    monkeypatch.setenv(
        "COMMUNITYLAB_PROVEEDOR_ANALISIS",
        PROVEEDOR_NVIDIA_NIM,
    )

    cadena_nvidia = MagicMock()
    cadena_nvidia.invoke.side_effect = _Error400Normal()

    cadena_gemini = MagicMock()

    def obtener_cadena(proveedor):
        if proveedor == PROVEEDOR_NVIDIA_NIM:
            return cadena_nvidia

        if proveedor == PROVEEDOR_GEMINI:
            return cadena_gemini

        raise AssertionError(proveedor)

    with patch(
        "src.agentes.cadenas._obtener_cadena_analisis",
        side_effect=obtener_cadena,
    ):
        resultado = analizar_mensaje(
            _estado()
        )

    assert len(
        resultado.get("fallos", [])
    ) > 0

    cadena_nvidia.invoke.assert_called_once()
    cadena_gemini.invoke.assert_not_called()
