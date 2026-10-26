from src.agentes.estado_agente import EstadoAgente
from typing import cast

import logging
import threading
import time
from contextvars import ContextVar
from unittest.mock import patch

from src.agentes.grafo import procesar_estados_por_lotes
from src.agentes.observabilidad import contexto_ejecucion, registrar_evento


def test_dos_mensajes_simultaneos_conservan_orden_y_trazas(
    monkeypatch, caplog
):
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_MENSAJES", "2")

    marca = ContextVar[str | None]("marca_experimento", default=None)
    ids = [f"exp-{i}" for i in range(4)]
    estados: list[EstadoAgente] = [
        {
            "id": identificador,
            "texto": "Mensaje experimental",
            "errores": [],
            "fallos": [],
            "rutas": [],
            "activos_generados": {},
        }

        for identificador in ids
    ]

    activos = 0
    max_activos = 0
    bloqueo = threading.Lock()

    def analizar(grupo):
        return [
            {
                "sentimiento": "neutral",
                "tipo_detectado": "comentario",
                "errores": [],
                "fallos": [],
            }
            for _ in grupo
        ]

    def invocar(estado):
        nonlocal activos, max_activos

        with bloqueo:
            activos += 1
            max_activos = max(max_activos, activos)

        try:
            time.sleep(0.08)
            registrar_evento(
                "prueba_concurrencia",
                id_interaccion=estado["id"],
            )
            return {**estado, "marca": marca.get()}
        finally:
            with bloqueo:
                activos -= 1

    token = marca.set("contexto-original")
    try:
        with (
            contexto_ejecucion("ejecucion-experimental"),
            caplog.at_level(
                logging.INFO,
                logger="communitylab.ciencia_datos",
            ),
            patch(
                "src.agentes.grafo.analizar_lote",
                side_effect=analizar,
            ),
            patch(
                "src.agentes.grafo.grafo_desde_analisis.invoke",
                side_effect=invocar,
            ),
        ):
            resultados = procesar_estados_por_lotes(
                estados,
                ids_contenido=set(),
            )
    finally:
        marca.reset(token)

    assert max_activos == 2
    assert [r["id"] for r in resultados] == ids
    assert all(cast(dict, r)["marca"] == "contexto-original" for r in resultados)

    registros = [
        r for r in caplog.records
        if getattr(r, "evento", None) == "prueba_concurrencia"
    ]
    assert len(registros) == 4
    assert all(
        r.id_ejecucion == "ejecucion-experimental"
        for r in registros
    )


def test_fallo_analisis_no_detiene_mensajes_concurrentes(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_MENSAJES", "2")

    estados: list[EstadoAgente] = [
        {
            "id": f"test-{i}",
            "texto": f"Mensaje {i}",
            "errores": [],
            "fallos": [],
            "rutas": [],
            "activos_generados": {},
        }
        for i in range(3)
    ]

    def analizar(grupo):
        return [
            {
                "errores": ["Fallo simulado"] if e["id"] == "test-1" else [],
                "fallos": [],
            }
            for e in grupo
        ]

    procesados = []

    def invocar(estado):
        procesados.append(estado["id"])
        return {**estado, "procesado": True}

    with (
        patch("src.agentes.grafo.analizar_lote", side_effect=analizar),
        patch(
            "src.agentes.grafo.grafo_desde_analisis.invoke",
            side_effect=invocar,
        ),
    ):
        resultados = procesar_estados_por_lotes(
            estados, ids_contenido=set()
        )

    assert [r["id"] for r in resultados] == [
        "test-0", "test-1", "test-2"
    ]
    assert set(procesados) == {"test-0", "test-2"}
    assert cast(dict, resultados[1])["errores"] == ["Fallo simulado"]
    assert cast(dict, resultados[1])["activos_generados"] == {}
    assert cast(dict, resultados[0])["procesado"] is True
    assert cast(dict, resultados[2])["procesado"] is True


def test_configuracion_experimental_super_en_todos_los_tiers(monkeypatch):
    from src.agentes import configuracion_ia as config

    modelo = "nvidia/nemotron-3-super-120b-a12b"

    monkeypatch.setenv("COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO", "true")

    for tier in ("RAPIDO", "ESTANDAR", "RAZONAMIENTO"):
        monkeypatch.setenv(
            f"COMMUNITYLAB_MODELO_NVIDIA_{tier}", modelo
        )

    with patch.object(config, "load_dotenv", return_value=None):
        for tier in ("rapido", "estandar", "razonamiento"):
            assert config.obtener_modelo_nvidia_por_tier(tier) == modelo


def test_excepcion_inesperada_no_interrumpe_lote(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_MENSAJES", "2")

    estados: list[EstadoAgente] = [
        {
            "id": f"exp-{i}",
            "texto": f"Mensaje experimental {i}",
            "errores": [],
            "fallos": [],
            "rutas": [],
            "activos_generados": {},
        }
        for i in range(4)
    ]

    def analizar(grupo):
        return [
            {
                "sentimiento": "neutral",
                "tipo_detectado": "comentario",
                "errores": [],
                "fallos": [],
            }
            for _ in grupo
        ]

    def invocar(estado):
        if estado["id"] == "exp-1":
            raise RuntimeError("Fallo inesperado del trabajador")

        return {
            **estado,
            "procesado": True,
        }

    with (
        patch(
            "src.agentes.grafo.analizar_lote",
            side_effect=analizar,
        ),
        patch(
            "src.agentes.grafo.grafo_desde_analisis.invoke",
            side_effect=invocar,
        ),
    ):
        resultados = procesar_estados_por_lotes(
            estados,
            ids_contenido=set(),
        )

    assert [r["id"] for r in resultados] == [
        "exp-0", "exp-1", "exp-2", "exp-3"
    ]

    for indice in (0, 2, 3):
        assert cast(dict, resultados[indice])["procesado"] is True
        assert cast(dict, resultados[indice])["errores"] == []

    fallido = resultados[1]

    assert cast(dict, fallido)["errores"]
    assert cast(dict, fallido)["activos_generados"] == {}
    assert len(cast(dict, fallido)["fallos"]) == 1

    fallo = cast(dict, fallido)["fallos"][0]

    assert fallo["id"] == "exp-1"
    assert fallo["etapa"] == "procesar_grafo"
    assert fallo["tipo_error"] == "RuntimeError"
    assert "Fallo inesperado" in fallo["mensaje"]
