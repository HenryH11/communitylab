import threading
from unittest.mock import patch

from src.agentes.grafo import procesar_estados_por_lotes


def test_dos_lotes_de_analisis_en_paralelo_conservan_orden(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS", "2")
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_MENSAJES", "1")

    bloqueo = threading.Lock()
    segundo_lote_iniciado = threading.Event()
    activos = 0
    maximo_simultaneo = 0

    estados = [
        {
            "id": f"prueba-{i}",
            "texto": f"Mensaje {i}",
            "tipo_original": "comentario",
            "score_relevancia": 50,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        }
        for i in range(4)
    ]

    def analizar_falso(grupo):
        nonlocal activos, maximo_simultaneo

        with bloqueo:
            activos += 1
            maximo_simultaneo = max(maximo_simultaneo, activos)
            if activos == 2:
                segundo_lote_iniciado.set()

        segundo_lote_iniciado.wait(timeout=1.5)

        with bloqueo:
            activos -= 1

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
        side_effect=analizar_falso,
    ), patch(
        "src.agentes.grafo.grafo_desde_analisis.invoke",
        side_effect=lambda estado: estado,
    ):
        resultados = procesar_estados_por_lotes(
            estados,
            ids_contenido=set(),
            tamano_lote=2,
        )

    assert maximo_simultaneo == 2
    assert [r["id"] for r in resultados] == [
        "prueba-0",
        "prueba-1",
        "prueba-2",
        "prueba-3",
    ]


def _estados_prueba_lotes():
    return [
        {
            "id": f"lote-{i}",
            "texto": f"Mensaje {i}",
            "tipo_original": "comentario",
            "score_relevancia": 50,
            "rutas": [],
            "activos_generados": {},
            "errores": [],
            "fallos": [],
        }
        for i in range(4)
    ]


def _analisis_prueba(grupo):
    return [
        {
            "sentimiento": "neutral",
            "tema_principal": "comunidad",
            "subtema": "prueba de concurrencia",
            "tipo_detectado": "comentario",
        }
        for _ in grupo
    ]


def test_fallo_de_un_lote_no_interrumpe_los_demas(monkeypatch):
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS", "2")
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_MENSAJES", "1")

    def analizar(grupo):
        if grupo[0]["id"] == "lote-0":
            raise RuntimeError("Fallo simulado del primer lote")
        return _analisis_prueba(grupo)

    with patch(
        "src.agentes.grafo.analizar_lote",
        side_effect=analizar,
    ), patch(
        "src.agentes.grafo.grafo_desde_analisis.invoke",
        side_effect=lambda estado: estado,
    ) as invocar:
        resultados = procesar_estados_por_lotes(
            _estados_prueba_lotes(),
            ids_contenido=set(),
            tamano_lote=2,
        )

    assert [r["id"] for r in resultados] == [
        "lote-0", "lote-1", "lote-2", "lote-3"
    ]

    for resultado in resultados[:2]:
        assert resultado["errores"]
        assert resultado["rutas"] == []
        assert resultado["activos_generados"] == {}
        assert len(resultado["fallos"]) == 1
        assert resultado["fallos"][0]["id"] == resultado["id"]
        assert resultado["fallos"][0]["etapa"] == "analizar_lote"
        assert resultado["fallos"][0]["tipo_error"] == "RuntimeError"

    for resultado in resultados[2:]:
        assert resultado["sentimiento"] == "neutral"
        assert not resultado["errores"]

    assert invocar.call_count == 2


def test_contexto_ejecucion_se_propaga_a_ambos_lotes(monkeypatch):
    from src.agentes.observabilidad import (
        contexto_ejecucion,
        registrar_evento,
    )

    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS", "2")
    monkeypatch.setenv("COMMUNITYLAB_CONCURRENCIA_MENSAJES", "1")

    def analizar(grupo):
        registrar_evento(
            "prueba_contexto_lote",
            ids_interaccion=[estado["id"] for estado in grupo],
        )
        return _analisis_prueba(grupo)

    with patch(
        "src.agentes.grafo.analizar_lote",
        side_effect=analizar,
    ), patch(
        "src.agentes.grafo.grafo_desde_analisis.invoke",
        side_effect=lambda estado: estado,
    ), patch(
        "src.agentes.observabilidad.LOGGER.log",
    ) as registrar:
        with contexto_ejecucion("prueba-concurrencia-lotes"):
            resultados = procesar_estados_por_lotes(
                _estados_prueba_lotes(),
                ids_contenido=set(),
                tamano_lote=2,
            )

    eventos = [
        llamada
        for llamada in registrar.call_args_list
        if llamada.args[1] == "prueba_contexto_lote"
    ]

    assert len(resultados) == 4
    assert len(eventos) == 2
    assert all(
        llamada.kwargs["extra"]["id_ejecucion"]
        == "prueba-concurrencia-lotes"
        for llamada in eventos
    )


import pytest


@pytest.mark.parametrize(
    "valor",
    ["0", "3", "-1", "abc", "", "2.5"],
)
def test_configuracion_concurrencia_lotes_invalida(
    monkeypatch, valor
):
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
        valor,
    )

    with patch(
        "src.agentes.grafo.analizar_lote"
    ) as analizar:
        with pytest.raises(
            ValueError,
            match="COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
        ):
            procesar_estados_por_lotes(
                _estados_prueba_lotes(),
                ids_contenido=set(),
                tamano_lote=2,
            )

    analizar.assert_not_called()


def test_lote_incompleto_no_pierde_mensajes(monkeypatch):
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS", "2"
    )
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_MENSAJES", "1"
    )

    estados = _estados_prueba_lotes()

    def analizar(grupo):
        if grupo[0]["id"] == "lote-0":
            return _analisis_prueba(grupo[:1])
        return _analisis_prueba(grupo)

    with patch(
        "src.agentes.grafo.analizar_lote",
        side_effect=analizar,
    ), patch(
        "src.agentes.grafo.grafo_desde_analisis.invoke",
        side_effect=lambda estado: estado,
    ):
        resultados = procesar_estados_por_lotes(
            estados,
            ids_contenido=set(),
            tamano_lote=2,
        )

    assert [r["id"] for r in resultados] == [
        "lote-0", "lote-1", "lote-2", "lote-3"
    ]

    faltante = resultados[1]
    assert faltante["errores"]
    assert faltante["fallos"][0]["id"] == "lote-1"


@pytest.mark.parametrize("trabajadores", [1, 2])
def test_lote_con_resultados_excedentes(monkeypatch, trabajadores):
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
        str(trabajadores),
    )
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_MENSAJES", "1"
    )

    estados = _estados_prueba_lotes()

    def analizar(grupo):
        resultados = _analisis_prueba(grupo)
        if grupo[0]["id"] == "lote-0":
            return resultados + [resultados[0]]
        return resultados

    with patch(
        "src.agentes.grafo.analizar_lote",
        side_effect=analizar,
    ), patch(
        "src.agentes.grafo.grafo_desde_analisis.invoke",
        side_effect=lambda estado: estado,
    ):
        resultados = procesar_estados_por_lotes(
            estados,
            ids_contenido=set(),
            tamano_lote=2,
        )

    assert [r["id"] for r in resultados] == [
        "lote-0", "lote-1", "lote-2", "lote-3"
    ]

    for resultado in resultados[:2]:
        assert resultado["errores"]
        assert resultado["fallos"][0]["id"] == resultado["id"]
        assert resultado["fallos"][0]["etapa"] == "analizar_lote"

    for resultado in resultados[2:]:
        assert not resultado.get("errores")
        assert resultado["sentimiento"] == "neutral"


@pytest.mark.parametrize("trabajadores", [1, 2])
def test_excepcion_inesperada_mantiene_ids_en_ambos_modos(
    monkeypatch, trabajadores
):
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS",
        str(trabajadores),
    )
    monkeypatch.setenv(
        "COMMUNITYLAB_CONCURRENCIA_MENSAJES", "1"
    )

    def analizar(grupo):
        if grupo[0]["id"] == "lote-0":
            raise RuntimeError("Fallo inesperado de prueba")
        return _analisis_prueba(grupo)

    with patch(
        "src.agentes.grafo.analizar_lote",
        side_effect=analizar,
    ), patch(
        "src.agentes.grafo.grafo_desde_analisis.invoke",
        side_effect=lambda estado: estado,
    ):
        resultados = procesar_estados_por_lotes(
            _estados_prueba_lotes(),
            ids_contenido=set(),
            tamano_lote=2,
        )

    assert [r["id"] for r in resultados] == [
        "lote-0", "lote-1", "lote-2", "lote-3"
    ]

    assert all(r.get("errores") for r in resultados[:2])
    assert all(not r.get("errores") for r in resultados[2:])
    assert all(
        r["fallos"][0]["id"] == r["id"]
        for r in resultados[:2]
    )
