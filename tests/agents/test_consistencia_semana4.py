"""Tres perfiles: Datos -> grafo -> contrato, con cadenas de IA simuladas.

Verifica asociación por ID y preservación de contenido. No evalúa modelos reales,
no implementa el auditor semántico de Gustavo y no simula aprobación en la UI.
"""

from copy import deepcopy
import json
from pathlib import Path
import socket
from unittest.mock import Mock

import pytest

from src.agentes import modelos, reintentos
from src.agentes.entrega_resultados import entrega_resultados_a_json, preparar_entrega_resultados
from src.agentes.nodos import nodo_analizador, nodos_generadores
from src.agentes.nodos.nodo_enrutador import determinar_rutas
from src.agentes.procesamiento import procesar_paquete_entrega
from src.datos.entrega_ia import preparar_paquete_ia


RAIZ = Path(__file__).resolve().parents[2]
CASOS = json.loads((RAIZ / "tests/fixtures/casos_consistencia_semana4.json").read_text(encoding="utf-8"))
PERFILES = {p["perfil"]: p for p in CASOS["perfiles"]}
MODELOS = {
    "linkedin": modelos.PublicacionLinkedIn,
    "boletin": modelos.DestaqueBoletin,
    "caso_exito": modelos.CasoDeExito,
    "preguntas_frecuentes": modelos.SugerenciaPreguntasFrecuentes,
}


@pytest.fixture(autouse=True)
def sin_servicios_externos(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("COMMUNITYLAB_LOGS", "0")
    for variable in ("NVIDIA_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(variable, raising=False)

    def bloquear(*args, **kwargs):
        raise AssertionError("Estas pruebas no pueden acceder a la red")

    monkeypatch.setattr(socket.socket, "connect", bloquear)
    monkeypatch.setattr(socket.socket, "connect_ex", bloquear)
    monkeypatch.setattr(socket, "getaddrinfo", bloquear)
    monkeypatch.setattr(reintentos, "_esperar", lambda segundos: None)


def entrada(perfiles, cantidad=10):
    """Autores sintéticos distintos conservan recurrencias válidas entre personas.

    Diez mensajes válidos permiten un ciclo real sin alterar el mínimo del plan.
    Las repeticiones prueban transporte e identidad, no diversidad semántica.
    """
    mensajes, referencias = [], {}
    for perfil in perfiles:
        for indice in range(cantidad):
            caso = PERFILES[perfil]
            mensaje = deepcopy(caso["entrada"])
            mensaje.update(id=f"s4-{perfil}-{indice}", autor=f"{mensaje['autor']} {indice}")
            mensajes.append(mensaje)
            referencias[mensaje["id"]] = caso
    return {
        "origen_comunidad": "Pruebas_sinteticas_Semana4",
        "periodo_referencia": "Semana_04",
        "interacciones": mensajes,
    }, referencias


def contenido_esperado(caso, ruta, autor):
    texto = json.dumps(caso["activos_simulados"][ruta], ensure_ascii=False)
    return json.loads(texto.replace("{autor}", autor))


def simular(monkeypatch, datos, referencias):
    por_autor = {m["autor"]: referencias[m["id"]] for m in datos["interacciones"]}

    def analizar(argumentos, **opciones):
        mensajes = json.loads(argumentos["mensajes_json"])
        # Desorden deliberado: el resultado debe asociarse por ID, no por posición.
        return {"resultados": [
            {"id": m["id"], **referencias[m["id"]]["analisis_simulado"]}
            for m in reversed(mensajes)
        ]}

    lote = Mock()
    lote.invoke.side_effect = analizar
    individual = Mock()
    individual.invoke.side_effect = AssertionError("No se espera análisis individual")
    monkeypatch.setattr(nodo_analizador, "cadena_analisis_lote", lote)
    monkeypatch.setattr(nodo_analizador, "cadena_analisis", individual)
    generadores = {}
    for ruta, modelo in MODELOS.items():
        def generar(contexto, ruta=ruta, modelo=modelo, **opciones):
            caso = por_autor[contexto["autor"]]
            assert contexto["texto"] == caso["entrada"]["texto"]
            return modelo.model_validate(contenido_esperado(caso, ruta, contexto["autor"]))
        generadores[ruta] = Mock()
        generadores[ruta].invoke.side_effect = generar
    obtener = Mock(return_value=generadores)
    monkeypatch.setattr(nodos_generadores, "_obtener_generadores", obtener)
    return lote, individual, obtener, generadores


@pytest.mark.parametrize("perfiles", [
    ("exito",), ("duda_tecnica",), ("spam",),
    ("exito", "duda_tecnica", "spam"),
])
def test_perfiles_conservan_identidad_contenido_y_exclusion(perfiles, monkeypatch):
    datos, referencias = entrada(perfiles)
    original = deepcopy(datos)
    lote, individual, obtener, generadores = simular(monkeypatch, datos, referencias)
    paquete = preparar_paquete_ia(datos, fecha_referencia=CASOS["fecha_referencia"], tamano_ciclo=10)
    entrega = preparar_entrega_resultados(procesar_paquete_entrega(paquete))
    entrega = json.loads(entrega_resultados_a_json(entrega))

    validos = {m["id"]: m for m in datos["interacciones"] if referencias[m["id"]]["analisis_simulado"]}
    ruido = set(referencias) - set(validos)
    assert datos == original
    assert entrega["fallos"] == []
    assert entrega["ids_pendientes"] == []
    assert entrega["pendientes"] == []
    assert len(entrega["interacciones"]) == len(validos)
    assert {m["id"] for m in entrega["interacciones"]} == set(validos)
    assert {e["id"] for e in paquete["estados"]} == set(validos)
    assert set(paquete["plan"]["ids_contenido"]) == set(validos)
    enviados = [m["id"] for llamada in lote.invoke.call_args_list
                for m in json.loads(llamada.args[0]["mensajes_json"])]
    assert len(enviados) == len(validos)
    assert set(enviados) == set(validos)
    individual.invoke.assert_not_called()

    activos_esperados = {}
    for resultado in entrega["interacciones"]:
        fuente = validos[resultado["id"]]
        caso = referencias[resultado["id"]]
        assert resultado["texto"] == fuente["texto"]
        assert resultado["autor"] == fuente["autor"]
        assert resultado["tipo_original"] == fuente["tipo"]
        assert resultado["tipo_detectado"] == caso["analisis_simulado"]["tipo_detectado"]
        assert set(resultado["rutas"]) == set(caso["activos_simulados"])
        for ruta in resultado["rutas"]:
            contenido = contenido_esperado(caso, ruta, fuente["autor"])
            if ruta == "linkedin":
                contenido["canal_recomendado"] = "LinkedIn Oficial"
            activos_esperados[(fuente["id"], ruta)] = contenido
            assert resultado["activos_generados"][ruta] == contenido

    # Una búsqueda de fragmentos global no detectaría activos cruzados entre IDs.
    activos = {(a["id_interaccion"], a["tipo"]): a["contenido"] for a in entrega["activos"]}
    assert len(entrega["activos"]) == len(activos_esperados)
    assert activos == activos_esperados
    revisiones = {e["id"]: e for l in paquete["informe"]["lotes"] for e in l["evaluaciones"]}
    for identificador in ruido:
        assert revisiones[identificador]["incluido_sentimiento"] is False
        assert PERFILES["spam"]["motivo_exclusion"] in revisiones[identificador]["motivos_exclusion_sentimiento"]
    assert sum(g.invoke.call_count for g in generadores.values()) == len(activos_esperados)
    if not validos:
        lote.invoke.assert_not_called()
        obtener.assert_not_called()


@pytest.mark.parametrize("sentimiento", ["neutral", "negativo"])
def test_int020_feedback_conserva_ruta_con_ambos_sentimientos(sentimiento):
    fixture = json.loads((RAIZ / "tests/fixtures/casos_referencia_ia_candidatos.json").read_text(encoding="utf-8"))
    caso = next(c for c in fixture["interacciones"] if c["id"] == "int-020")
    estado = {**caso, "sentimiento": sentimiento}
    original = deepcopy(estado)
    assert determinar_rutas(estado) == {"rutas": ["insight_mejora"]}
    assert estado == original
    assert estado["tipo_original"] == "feedback"


def test_int020_divergencia_de_tipo_puede_perder_insight_sin_cambiar_original():
    fixture = json.loads((RAIZ / "tests/fixtures/casos_referencia_ia_candidatos.json").read_text(encoding="utf-8"))
    caso = next(c for c in fixture["interacciones"] if c["id"] == "int-020")
    estado = {**caso, "tipo_detectado": "comentario"}
    original = deepcopy(estado)
    assert determinar_rutas(estado) == {"rutas": []}
    assert estado == original
    assert estado["tipo_original"] == "feedback"
