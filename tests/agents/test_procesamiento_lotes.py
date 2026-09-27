from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.agentes.grafo import (
    procesar_estados_por_lotes,
    procesar_paquete_entrega,
)
from src.agentes.modelos import AnalisisLote, AnalisisMensaje, AnalisisMensajeConId
from src.agentes.nodos.nodo_analizador import analizar_lote
from src.agentes.nodos.nodos_generadores import (
    SugerenciaPreguntasFrecuentes,
    generar_activos,
)


def crear_estado(mensaje_id, puntaje=80):
    return {
        "id": mensaje_id,
        "autor": "Ana",
        "canal": "#ayuda",
        "origen": "Discord",
        "idioma": "es",
        "tipo_original": "pregunta_tecnica",
        "score_relevancia": puntaje,
        "texto": f"Mensaje de prueba {mensaje_id}",
        "rutas": [],
        "activos_generados": {},
        "errores": [],
    }


def crear_analisis(mensaje_id, tipo="pregunta_tecnica", sentimiento="neutral"):
    return AnalisisMensajeConId(
        id=mensaje_id,
        sentimiento=sentimiento,
        tema_principal="datos_ia",
        subtema="prueba por lotes",
        tipo_detectado=tipo,
    )


def test_analizar_lote_asocia_resultados_por_id_aunque_lleguen_reordenados():
    estados = [crear_estado("id-a"), crear_estado("id-b")]
    cadena_lote = MagicMock()
    cadena_lote.invoke.return_value = AnalisisLote(
        resultados=[
            crear_analisis("id-b", tipo="feedback"),
            crear_analisis("id-a", tipo="testimonio"),
        ]
    )

    with patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis_lote",
        cadena_lote,
    ):
        resultados = analizar_lote(estados)

    assert [resultado["tipo_detectado"] for resultado in resultados] == [
        "testimonio",
        "feedback",
    ]
    assert json_ids(cadena_lote.invoke.call_args.args[0]["mensajes_json"]) == [
        "id-a",
        "id-b",
    ]


def json_ids(mensajes_json):
    import json

    return [mensaje["id"] for mensaje in json.loads(mensajes_json)]


def test_analizar_lote_reintenta_individualmente_solo_ids_omitidos():
    estados = [crear_estado("id-a"), crear_estado("id-b")]
    cadena_lote = MagicMock()
    cadena_lote.invoke.return_value = AnalisisLote(
        resultados=[crear_analisis("id-a")]
    )
    cadena_individual = MagicMock()
    cadena_individual.invoke.return_value = AnalisisMensaje(
        sentimiento="positivo",
        tema_principal="aprendizaje",
        subtema="progreso del curso",
        tipo_detectado="testimonio",
    )

    with patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis_lote",
        cadena_lote,
    ), patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis",
        cadena_individual,
    ):
        resultados = analizar_lote(estados)

    cadena_individual.invoke.assert_called_once()
    assert resultados[0]["tipo_detectado"] == "pregunta_tecnica"
    assert resultados[1]["tipo_detectado"] == "testimonio"


def test_analizar_lote_reintenta_solo_el_id_duplicado():
    estados = [crear_estado("id-a"), crear_estado("id-b")]
    cadena_lote = MagicMock()
    cadena_lote.invoke.return_value = AnalisisLote(
        resultados=[
            crear_analisis("id-a"),
            crear_analisis("id-a", tipo="feedback"),
            crear_analisis("id-b"),
        ]
    )
    cadena_individual = MagicMock()
    cadena_individual.invoke.return_value = AnalisisMensaje(
        sentimiento="positivo",
        tema_principal="comunidad",
        subtema="soporte recibido",
        tipo_detectado="comentario",
    )

    with patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis_lote",
        cadena_lote,
    ), patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis",
        cadena_individual,
    ):
        resultados = analizar_lote(estados)

    cadena_individual.invoke.assert_called_once()
    assert resultados[0]["tipo_detectado"] == "comentario"
    assert resultados[1]["tipo_detectado"] == "pregunta_tecnica"


def test_fallo_total_del_lote_no_dispara_reintentos_individuales():
    estados = [crear_estado("id-a"), crear_estado("id-b")]
    cadena_lote = MagicMock()
    cadena_lote.invoke.side_effect = RuntimeError("API no disponible")
    cadena_individual = MagicMock()

    with patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis_lote",
        cadena_lote,
    ), patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis",
        cadena_individual,
    ):
        resultados = analizar_lote(estados)

    cadena_individual.invoke.assert_not_called()
    assert all(resultado.get("errores") for resultado in resultados)


def test_respuesta_de_lote_malformada_se_reporta_sin_reintentos_en_cascada():
    estados = [crear_estado("id-a"), crear_estado("id-b")]
    cadena_lote = MagicMock()
    cadena_lote.invoke.return_value = {"resultados": "respuesta inválida"}
    cadena_individual = MagicMock()

    with patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis_lote",
        cadena_lote,
    ), patch(
        "src.agentes.nodos.nodo_analizador.cadena_analisis",
        cadena_individual,
    ):
        resultados = analizar_lote(estados)

    cadena_individual.invoke.assert_not_called()
    assert all(resultado.get("errores") for resultado in resultados)


def test_id_de_contenido_controla_enrutamiento_y_el_puntaje_bajo_se_analiza():
    estado = crear_estado("int-008", puntaje=39)
    analisis = {
        "sentimiento": "positivo",
        "tema_principal": "aprendizaje",
        "subtema": "progreso del curso",
        "tipo_detectado": "testimonio",
    }

    with patch(
        "src.agentes.grafo.analizar_lote",
        return_value=[analisis],
    ):
        resultado = procesar_estados_por_lotes(
            [estado],
            ids_contenido={"int-022", "int-002"},
        )[0]

    assert resultado["sentimiento"] == "positivo"
    assert resultado["rutas"] == []
    assert resultado["activos_generados"] == {}
    assert resultado["elegible_contenido"] is False


def test_estado_por_lotes_se_subdivide_sin_perder_orden_ni_ids():
    estados = [crear_estado(f"id-{indice}") for indice in range(3)]
    grupos_analizados = []

    def analizar_grupo(grupo):
        grupos_analizados.append(
            [estado["id"] for estado in grupo]
        )
        return [
            {
                "sentimiento": "neutral",
                "tema_principal": "comunidad",
                "subtema": "mensaje de prueba",
                "tipo_detectado": "comentario",
            }
            for _ in grupo
        ]

    with patch(
        "src.agentes.grafo.analizar_lote",
        side_effect=analizar_grupo,
    ):
        resultados = procesar_estados_por_lotes(
            estados,
            ids_contenido=set(),
            tamano_lote=2,
        )

    assert grupos_analizados == [["id-0", "id-1"], ["id-2"]]
    assert [estado["id"] for estado in resultados] == [
        "id-0",
        "id-1",
        "id-2",
    ]


def test_elegibilidad_por_id_prevalece_sobre_puntaje_en_enrutamiento():
    estado = crear_estado("int-022", puntaje=39)
    analisis = {
        "sentimiento": "neutral",
        "tema_principal": "datos_ia",
        "subtema": "enrutador LangGraph",
        "tipo_detectado": "pregunta_tecnica",
    }
    generador_preguntas_frecuentes = MagicMock()
    generador_preguntas_frecuentes.invoke.return_value = SugerenciaPreguntasFrecuentes(
        tema="Enrutador",
        respuesta="Respuesta de prueba.",
    )

    with patch(
        "src.agentes.grafo.analizar_lote",
        return_value=[analisis],
    ), patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores",
        return_value={"preguntas_frecuentes": generador_preguntas_frecuentes},
    ):
        resultado = procesar_estados_por_lotes(
            [estado],
            ids_contenido={"int-022"},
        )[0]

    assert resultado["rutas"] == ["preguntas_frecuentes"]
    assert (
        resultado["activos_generados"]["preguntas_frecuentes"]["tema"]
        == "Enrutador"
    )


def test_procesar_paquete_sigue_ciclos_por_id_y_devuelve_pendientes():
    estados = [crear_estado("id-a"), crear_estado("id-b"), crear_estado("id-c")]
    paquete = {
        "estados": estados,
        "plan": {
            "ids_contenido": ["id-b"],
            "ciclos": [{"indice": 0, "cantidad": 2, "ids": ["id-b", "id-a"]}],
            "pendientes": ["id-c"],
        },
    }
    llamadas = []

    def procesar_grupo(grupo, *, ids_contenido, tamano_lote):
        llamadas.append((grupo, ids_contenido, tamano_lote))
        return [dict(estado, rutas=[]) for estado in grupo]

    with patch(
        "src.agentes.grafo.procesar_estados_por_lotes",
        side_effect=procesar_grupo,
    ):
        resultado = procesar_paquete_entrega(paquete)

    assert [estado["id"] for estado in llamadas[0][0]] == ["id-b", "id-a"]
    assert llamadas[0][1] == {"id-b"}
    assert [estado["id"] for estado in resultado["pendientes"]] == ["id-c"]
    assert set(resultado["resultados_por_id"]) == {"id-a", "id-b"}


def test_procesar_paquete_rechaza_planes_que_no_cubren_todos_los_ids():
    paquete = {
        "estados": [crear_estado("id-a")],
        "plan": {
            "ids_contenido": [],
            "ciclos": [],
            "pendientes": [],
        },
    }

    with pytest.raises(ValueError, match="no cubren todos los estados"):
        procesar_paquete_entrega(paquete)


def test_sin_rutas_no_inicializa_generadores_ni_requiere_gemini():
    with patch(
        "src.agentes.nodos.nodos_generadores._obtener_generadores"
    ) as obtener_generadores:
        resultado = generar_activos({"rutas": [], "errores": []})

    obtener_generadores.assert_not_called()
    assert resultado == {"activos_generados": {}, "errores": []}
