"""Recorrido Datos -> grafo -> contrato DS con fallos inyectados y sin red."""

from copy import deepcopy
import json
from unittest.mock import MagicMock

import pytest

from src.agentes.entrega_resultados import (
    entrega_resultados_a_json,
    preparar_entrega_resultados,
)
from src.agentes.grafo import procesar_paquete_entrega
from src.agentes.nodos import nodo_analizador, nodos_generadores
from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.ingesta import cargar_json


FECHA = "2026-09-17T12:00:00Z"


def entrada(cantidad=10):
    return {
        "origen_comunidad": "Pruebas_Semana3",
        "periodo_referencia": "Semana_03",
        "interacciones": [
            {
                "id": f"s3-{i}", "autor": f"Persona {i}", "canal": "#dudas",
                "tipo": "pregunta_tecnica", "idioma": "es",
                "texto": f"¿Cómo resuelvo el error {i} en Python y LangGraph? 👩‍💻",
                "fecha": "2026-09-16T12:00:00Z",
            }
            for i in range(cantidad)
        ],
    }


def analisis(identificador=None):
    resultado = {
        "sentimiento": "neutral", "tema_principal": "datos_ia",
        "subtema": "Errores de programación", "tipo_detectado": "pregunta_tecnica",
    }
    if identificador is not None:
        resultado["id"] = identificador
    return resultado


def respuesta_lote(argumentos):
    mensajes = json.loads(argumentos["mensajes_json"])
    return {"resultados": [analisis(m["id"]) for m in mensajes]}


@pytest.fixture
def servicios(monkeypatch):
    """Solo se sustituyen las llamadas a modelos; el grafo y contratos son reales."""
    lote = MagicMock()
    lote.invoke.side_effect = respuesta_lote
    individual = MagicMock()
    individual.invoke.side_effect = AssertionError("Llamada individual inesperada")
    faq = MagicMock()
    faq.invoke.return_value = nodos_generadores.SugerenciaPreguntasFrecuentes(
        tema="Python", respuesta="Revisa el mensaje de error y un ejemplo mínimo."
    )
    generadores = MagicMock(return_value={"preguntas_frecuentes": faq})
    monkeypatch.setattr(nodo_analizador, "cadena_analisis_lote", lote)
    monkeypatch.setattr(nodo_analizador, "cadena_analisis", individual)
    monkeypatch.setattr(nodos_generadores, "_obtener_generadores", generadores)
    return lote, individual, faq, generadores


def ejecutar(datos):
    paquete = preparar_paquete_ia(datos, fecha_referencia=FECHA, tamano_ciclo=10)
    salida = procesar_paquete_entrega(paquete)
    return paquete, preparar_entrega_resultados(salida)


@pytest.mark.parametrize("campo,valor", [
    ("texto", None), ("texto", 123), ("texto", "\ud800"),
    ("autor", None), ("tipo", "tipo_desconocido"), ("fecha", "sin-fecha"),
    ("id", "s3-0"),
])
def test_entrada_invalida_se_rechaza_antes_de_llamar_ia(campo, valor, servicios):
    datos = entrada()
    datos["interacciones"][1][campo] = valor
    original = deepcopy(datos)
    with pytest.raises(ValueError):
        ejecutar(datos)
    assert datos == original
    servicios[0].invoke.assert_not_called()
    servicios[1].invoke.assert_not_called()
    servicios[3].assert_not_called()


def test_campo_ausente_se_rechaza_antes_de_llamar_ia(servicios):
    datos = entrada()
    del datos["interacciones"][0]["texto"]
    with pytest.raises(ValueError, match="texto"):
        ejecutar(datos)
    servicios[0].invoke.assert_not_called()


@pytest.mark.parametrize("cuerpo", [b'{"lotes": [', b'{"texto": "\xff"}'])
def test_archivo_corrupto_no_llega_al_grafo(cuerpo, tmp_path, servicios):
    archivo = tmp_path / "entrada.json"
    archivo.write_bytes(cuerpo)
    with pytest.raises(ValueError):
        ejecutar(cargar_json(archivo))
    assert archivo.read_bytes() == cuerpo
    servicios[0].invoke.assert_not_called()


def test_ruido_no_consume_ia_y_texto_unicode_llega_al_contrato(servicios):
    datos = entrada(14)
    textos = ["", "https://example.com", "spam spam spam spam spam spam", "[deleted]"]
    for mensaje, texto in zip(datos["interacciones"][-4:], textos):
        mensaje["texto"] = texto
    original = deepcopy(datos)
    paquete, entrega = ejecutar(datos)
    assert len(paquete["estados"]) == 10
    assert paquete["informe"]["resumen_sentimiento"]["excluidas_calidad"] == 4
    enviados = json.loads(servicios[0].invoke.call_args.args[0]["mensajes_json"])
    assert [m["id"] for m in enviados] == [f"s3-{i}" for i in range(10)]
    assert entrega["resumen_comunidad"]["total_con_activos"] == 10
    assert datos == original
    serializado = entrega_resultados_a_json(entrega).encode("utf-8")
    assert "👩‍💻".encode("utf-8") in serializado
    assert json.loads(serializado)["interacciones"][0]["texto"] == original["interacciones"][0]["texto"]


def test_sin_ciclo_suficiente_conserva_pendientes_sin_llamadas(servicios):
    paquete, entrega = ejecutar(entrada(9))
    assert entrega["interacciones"] == []
    assert entrega["ids_pendientes"] == paquete["plan"]["pendientes"]
    assert len(entrega["pendientes"]) == 9
    servicios[0].invoke.assert_not_called()
    servicios[3].assert_not_called()


@pytest.mark.parametrize("fallo", [TimeoutError("espera agotada"), RuntimeError("HTTP 429 simulado")])
def test_fallo_de_un_lote_conserva_ids_y_permite_el_siguiente(fallo, servicios):
    lote, individual, faq, _ = servicios
    contador = 0

    def proveedor(argumentos):
        nonlocal contador
        contador += 1
        if contador == 1:
            raise fallo
        return respuesta_lote(argumentos)

    lote.invoke.side_effect = proveedor
    paquete, entrega = ejecutar(entrada(25))
    assert lote.invoke.call_count == 2
    individual.invoke.assert_not_called()
    assert faq.invoke.call_count == 10
    assert len(entrega["interacciones"]) == 20
    assert entrega["ids_pendientes"] == paquete["plan"]["pendientes"]
    assert len(entrega["pendientes"]) == 5
    assert entrega["resumen_comunidad"]["total_con_errores"] == 10
    assert entrega["resumen_comunidad"]["total_con_activos"] == 10
    assert {f["id"] for f in entrega["fallos"]} == {f"s3-{i}" for i in range(10)}
    assert all(f["etapa"] == "analizar_lote" for f in entrega["fallos"])
    assert all(not m["activos_generados"] for m in entrega["interacciones"][:10])


@pytest.mark.parametrize("respuesta", [None, {"resultados": "incorrecto"}, {"resultados": [{"id": "s3-0"}]}])
def test_respuesta_invalida_se_serializa_como_fallo_sin_generar(respuesta, servicios):
    servicios[0].invoke.side_effect = None
    servicios[0].invoke.return_value = respuesta
    _, entrega = ejecutar(entrada())
    assert entrega["resumen_comunidad"]["total_con_errores"] == 10
    assert entrega["activos"] == []
    assert len(json.loads(entrega_resultados_a_json(entrega))["fallos"]) == 10
    servicios[1].invoke.assert_not_called()
    servicios[3].assert_not_called()


def test_id_omitido_y_reintento_fallido_no_eliminan_resultados_validos(servicios):
    def omitir_uno(argumentos):
        respuesta = respuesta_lote(argumentos)
        respuesta["resultados"] = list(reversed(respuesta["resultados"][1:]))
        return respuesta

    servicios[0].invoke.side_effect = omitir_uno
    servicios[1].invoke.side_effect = TimeoutError("fallo individual simulado")
    _, entrega = ejecutar(entrada())
    servicios[1].invoke.assert_called_once()
    assert [m["id"] for m in entrega["interacciones"]] == [f"s3-{i}" for i in range(10)]
    assert entrega["resumen_comunidad"]["total_con_errores"] == 1
    assert entrega["resumen_comunidad"]["total_con_activos"] == 9
    assert entrega["fallos"][0]["id"] == "s3-0"
    assert entrega["fallos"][0]["etapa"] == "analizar_mensaje"


def test_fallo_de_generador_no_detiene_los_demas_mensajes(servicios):
    def generar(contexto):
        if "error 0 " in contexto["texto"]:
            raise RuntimeError("generador no disponible")
        return nodos_generadores.SugerenciaPreguntasFrecuentes(tema="Python", respuesta="Respuesta de prueba")

    servicios[2].invoke.side_effect = generar
    _, entrega = ejecutar(entrada())
    assert entrega["resumen_comunidad"]["total_con_errores"] == 1
    assert entrega["resumen_comunidad"]["total_con_activos"] == 9
    assert entrega["fallos"][0]["ruta"] == "preguntas_frecuentes"
    assert entrega["fallos"][0]["id"] == "s3-0"
