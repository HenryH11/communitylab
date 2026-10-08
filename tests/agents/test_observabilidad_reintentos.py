import json
import logging
import uuid
from typing import cast
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from src.agentes import reintentos
from src.agentes.entrega_resultados import preparar_entrega_resultados
from src.agentes.estado_agente import EstadoAgente
from src.agentes.procesamiento import procesar_paquete_entrega
from src.agentes.recuperacion import reprocesar_fallidos
from src.agentes.modelos import SugerenciaPreguntasFrecuentes
from src.agentes.nodos.nodos_generadores import generar_activos
from src.agentes.observabilidad import (
    FormateadorJson,
    ManejadorObservabilidad,
    config_ejecucion,
)
from src.agentes.reintentos import (
    FalloOperacion,
    ejecutar_con_reintentos,
    es_error_transitorio,
)

from src.agentes.errores_ia import (
    ErrorConfiguracionProveedor,
    ErrorSalidaProveedor,
)

LOGGER = "communitylab.ciencia_datos"


def _eventos(caplog, evento):
    return [registro for registro in caplog.records if getattr(registro, "evento", None) == evento]


def _estado_analizado(identificador, **extra) -> EstadoAgente:
    return cast(EstadoAgente, {
        "id": identificador,
        "autor": "Ana",
        "canal": "#ayuda",
        "origen": "Discord",
        "idioma": "es",
        "texto": f"Mensaje {identificador}",
        "tipo_original": "pregunta_tecnica",
        "score_relevancia": 80,
        "elegible_contenido": True,
        "elegible_faq": False,
        "sentimiento": "neutral",
        "tema_principal": "datos_ia",
        "subtema": "prueba",
        "tipo_detectado": "pregunta_tecnica",
        "rutas": ["preguntas_frecuentes"],
        "activos_generados": {},
        "errores": [],
        "fallos": [],
        **extra,
    })


@pytest.mark.parametrize(
    ("error", "esperado"),
    [
        (TimeoutError("timeout"), True),
        (ConnectionError("conexión cerrada"), True),
        (RuntimeError("429 RESOURCE_EXHAUSTED"), True),
        (RuntimeError("503 Service Unavailable"), True),
        (ValueError("falta GEMINI_API_KEY"), False),
        (RuntimeError("API no disponible"), False),
    ],
)
def test_clasifica_errores_transitorios(error, esperado):
    assert es_error_transitorio(error) is esperado


def test_reintenta_error_transitorio_y_recupera():
    operacion = MagicMock(side_effect=[TimeoutError("timeout"), "ok"])

    with patch.object(reintentos, "_esperar") as esperar:
        resultado = ejecutar_con_reintentos(operacion, contexto={"etapa": "prueba"})

    assert resultado == "ok"
    assert [llamada.args[0] for llamada in operacion.call_args_list] == [1, 2]
    esperar.assert_called_once()


def test_no_reintenta_error_permanente():
    operacion = MagicMock(side_effect=ValueError("esquema inválido"))

    with patch.object(reintentos, "_esperar") as esperar, pytest.raises(FalloOperacion) as fallo:
        ejecutar_con_reintentos(operacion, contexto={"etapa": "prueba"})

    assert fallo.value.intentos == 1
    assert fallo.value.reintentable is False
    esperar.assert_not_called()


def test_agota_intentos_y_deja_traceback_solo_en_log(caplog):
    operacion = MagicMock(side_effect=ConnectionError("conexión cerrada"))

    with caplog.at_level(logging.DEBUG, logger=LOGGER), patch.object(
        reintentos, "_esperar"
    ), pytest.raises(FalloOperacion) as fallo:
        ejecutar_con_reintentos(
            operacion,
            contexto={"etapa": "analizar_lote", "ids_interaccion": ["a"]},
        )

    assert fallo.value.intentos == reintentos.MAX_INTENTOS
    assert fallo.value.reintentable is True
    assert len(_eventos(caplog, "reintento_programado")) == reintentos.MAX_INTENTOS - 1

    registro_final = _eventos(caplog, "operacion_fallida")[0]
    linea = json.loads(FormateadorJson().format(registro_final))
    assert linea["etapa"] == "analizar_lote"
    assert linea["intentos"] == reintentos.MAX_INTENTOS
    assert "ConnectionError" in linea["traceback"]


def test_generacion_reintenta_solo_la_ruta_transitoria():
    generador = MagicMock()
    generador.invoke.side_effect = [
        TimeoutError("timeout"),
        SugerenciaPreguntasFrecuentes(tema="Tema", respuesta="Respuesta."),
    ]

    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        return_value={"preguntas_frecuentes": generador},
    ), patch.object(reintentos, "_esperar"):
        resultado = generar_activos(_estado_analizado("id-faq"))

    assert resultado["fallos"] == []
    assert resultado["activos_generados"]["preguntas_frecuentes"]["tema"] == "Tema"
    configuracion = generador.invoke.call_args.kwargs["config"]
    assert configuracion["metadata"] == {
        "etapa": "generar_activos",
        "intento": 2,
        "id_interaccion": "id-faq",
        "ruta": "preguntas_frecuentes",
    }


def test_fallo_transitorio_agotado_queda_marcado_como_reintentable():
    generador = MagicMock()
    generador.invoke.side_effect = TimeoutError("timeout")

    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        return_value={"preguntas_frecuentes": generador},
    ), patch.object(reintentos, "_esperar"):
        resultado = generar_activos(_estado_analizado("id-faq"))

    assert resultado["fallos"][0]["reintentable"] is True
    assert resultado["fallos"][0]["intentos"] == reintentos.MAX_INTENTOS


def test_reprocesar_regenera_solo_rutas_fallidas_y_conserva_activos():
    fallo = {
        "id": "id-mixto",
        "etapa": "generar_activos",
        "ruta": "preguntas_frecuentes",
        "tipo_error": "TimeoutError",
        "mensaje": "timeout",
        "intentos": 3,
        "reintentable": True,
    }
    resultado = _estado_analizado(
        "id-mixto",
        rutas=["caso_exito", "preguntas_frecuentes"],
        activos_generados={"caso_exito": {"titular": "Ya generado"}},
        errores=["generar_activos[preguntas_frecuentes]: TimeoutError: timeout"],
        fallos=[fallo],
    )
    generador_faq = MagicMock()
    generador_faq.invoke.return_value = SugerenciaPreguntasFrecuentes(
        tema="Tema", respuesta="Respuesta."
    )
    generador_caso = MagicMock()

    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        return_value={
            "preguntas_frecuentes": generador_faq,
            "caso_exito": generador_caso,
        },
    ):
        salida = reprocesar_fallidos(
            {"resultados": [resultado], "pendientes": [], "ids_pendientes": []}
        )

    nuevo = salida["resultados_por_id"]["id-mixto"]
    generador_caso.invoke.assert_not_called()
    assert nuevo["activos_generados"]["caso_exito"] == {"titular": "Ya generado"}
    assert nuevo["activos_generados"]["preguntas_frecuentes"]["tema"] == "Tema"
    assert nuevo["errores"] == []
    assert nuevo["fallos"] == []
    assert salida["reprocesamientos"] == [
        {"ids_intentados": ["id-mixto"], "ids_recuperados": ["id-mixto"]}
    ]


def test_reprocesar_reanaliza_fallo_de_analisis_y_respeta_elegibilidad():
    resultado = {
        **_estado_analizado("id-analisis"),
        "elegible_contenido": False,
        "rutas": [],
        "errores": ["analizar_lote: TimeoutError: timeout"],
        "fallos": [
            {
                "id": "id-analisis",
                "etapa": "analizar_lote",
                "tipo_error": "TimeoutError",
                "mensaje": "timeout",
                "intentos": 3,
                "reintentable": True,
            }
        ],
    }
    for campo in ("sentimiento", "tema_principal", "subtema", "tipo_detectado"):
        resultado.pop(campo)

    analisis = {
        "sentimiento": "neutral",
        "tema_principal": "datos_ia",
        "subtema": "reintento",
        "tipo_detectado": "pregunta_tecnica",
    }
    with patch("src.agentes.grafo.analizar_lote", return_value=[analisis]) as analizar:
        salida = reprocesar_fallidos(
            {"resultados": [resultado], "pendientes": [], "ids_pendientes": []}
        )

    estado_enviado = analizar.call_args.args[0][0]
    assert "errores" not in estado_enviado and "fallos" not in estado_enviado
    nuevo = salida["resultados"][0]
    assert nuevo["tipo_detectado"] == "pregunta_tecnica"
    assert nuevo["rutas"] == []
    assert nuevo.get("fallos", []) == []


def test_reprocesar_ignora_fallos_permanentes_por_defecto():
    resultado = _estado_analizado(
        "id-permanente",
        fallos=[
            {
                "id": "id-permanente",
                "etapa": "generar_activos",
                "ruta": "preguntas_frecuentes",
                "tipo_error": "ValidationError",
                "mensaje": "esquema inválido",
                "intentos": 1,
                "reintentable": False,
            }
        ],
    )

    with patch("src.agentes.nodos.nodos_generadores._obtener_generadores") as obtener:
        salida = reprocesar_fallidos(
            {"resultados": [resultado], "pendientes": [], "ids_pendientes": []}
        )

    obtener.assert_not_called()
    assert salida["resultados"][0].get("fallos") == resultado.get("fallos")


def test_procesar_paquete_recupera_fallos_transitorios_en_pasada_final():
    estado = _estado_analizado("id-a")
    paquete = {
        "estados": [estado],
        "plan": {
            "ids_contenido": ["id-a"],
            "ciclos": [{"indice": 0, "cantidad": 1, "ids": ["id-a"]}],
            "pendientes": [],
        },
    }
    con_fallo = {
        **estado,
        "fallos": [
            {
                "id": "id-a",
                "etapa": "analizar_lote",
                "tipo_error": "TimeoutError",
                "mensaje": "timeout",
                "intentos": 3,
                "reintentable": True,
            }
        ],
        "errores": ["analizar_lote: TimeoutError: timeout"],
    }

    procesar = MagicMock(side_effect=[[con_fallo], [estado]])
    with patch(
        "src.agentes.procesamiento.procesar_estados_por_lotes", procesar
    ), patch("src.agentes.recuperacion.procesar_estados_por_lotes", procesar):
        salida = procesar_paquete_entrega(paquete)

    assert procesar.call_count == 2
    assert salida["id_ejecucion"]
    assert salida["resultados"][0]["fallos"] == []
    assert salida["ciclos"][0]["resultados"][0]["fallos"] == []
    assert salida["reprocesamientos"][0]["ids_recuperados"] == ["id-a"]


def test_callback_registra_duracion_metadatos_y_tokens(caplog):
    manejador = ManejadorObservabilidad()
    run_id = uuid.uuid4()
    metadata = {
        **config_ejecucion("analizar_lote", intento=1, ids_interaccion=["a", "b"]).get(
            "metadata", {}
        ),
        "ls_model_name": "gemini-prueba",
    }
    respuesta = LLMResult(
        generations=[
            [
                ChatGeneration(
                    message=AIMessage(
                        content="{}",
                        usage_metadata={
                            "input_tokens": 3,
                            "output_tokens": 2,
                            "total_tokens": 5,
                        },
                    )
                )
            ]
        ]
    )

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        manejador.on_chat_model_start({}, [[]], run_id=run_id, metadata=metadata)
        manejador.on_llm_end(respuesta, run_id=run_id)

    campos = _eventos(caplog, "llm_fin")[0].campos
    assert campos["etapa"] == "analizar_lote"
    assert campos["ids_interaccion"] == ["a", "b"]
    assert campos["modelo"] == "gemini-prueba"
    assert campos["uso_tokens"] == {
        "input_tokens": 3,
        "output_tokens": 2,
        "total_tokens": 5,
    }
    assert campos["duracion_ms"] >= 0


def test_callback_registra_error_sin_traceback(caplog):
    manejador = ManejadorObservabilidad()
    run_id = uuid.uuid4()

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        manejador.on_llm_start({}, ["prompt"], run_id=run_id, metadata={"etapa": "generar_activos", "ruta": "linkedin"})
        manejador.on_llm_error(TimeoutError("timeout"), run_id=run_id)

    registro = _eventos(caplog, "llm_error")[0]
    assert registro.levelno == logging.WARNING
    assert registro.campos["ruta"] == "linkedin"
    assert registro.campos["tipo_error"] == "TimeoutError"
    assert not registro.exc_info


def test_contrato_expone_reintentables_e_id_ejecucion():
    reintentable = {
        "id": "id-a",
        "etapa": "generar_activos",
        "ruta": "linkedin",
        "tipo_error": "TimeoutError",
        "mensaje": "timeout",
        "intentos": 3,
        "reintentable": True,
    }
    permanente = {
        "id": "id-b",
        "etapa": "generar_activos",
        "ruta": "boletin",
        "tipo_error": "ValidationError",
        "mensaje": "esquema",
        "intentos": 1,
        "reintentable": False,
    }

    entrega = preparar_entrega_resultados(
        {
            "id_ejecucion": "abc123",
            "resultados": [
                _estado_analizado("id-a", errores=["x"], fallos=[reintentable]),
                _estado_analizado("id-b", errores=["y"], fallos=[permanente]),
            ],
            "pendientes": [],
            "ids_pendientes": [],
        }
    )

    assert entrega["version_contrato"] == "1.3"
    assert entrega["id_ejecucion"] == "abc123"
    assert entrega["ids_reintentables"] == ["id-a"]
    assert entrega["resumen_comunidad"]["total_fallos"] == 2
    assert entrega["resumen_comunidad"]["total_fallos_reintentables"] == 1


def test_salida_invalida_del_proveedor_es_reintentable():
    assert es_error_transitorio(
        ErrorSalidaProveedor("salida inválida")
    ) is True


def test_error_configuracion_proveedor_no_es_reintentable():
    assert es_error_transitorio(
        ErrorConfiguracionProveedor("falta NVIDIA_API_KEY")
    ) is False