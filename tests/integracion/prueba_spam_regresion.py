"""Evaluación explícita con proveedor real; consume cuota, sin persistencia cloud."""

import pytest

from src.agentes.estado_agente import EstadoAgente
from src.agentes.modelos import AnalisisMensaje
from src.agentes.nodos.nodo_analizador import analizar_lote, analizar_mensaje
from tests.casos_spam_regresion import CASOS


@pytest.mark.parametrize("modo", ["individual", "lote"])
@pytest.mark.parametrize("repeticion", range(2))
def test_quejas_legitimas_no_son_spam_y_captacion_si(modo, repeticion):
    estados: list[EstadoAgente] = [
        {"id": identificador, "texto": texto}
        for identificador, texto, _ in CASOS
    ]
    resultados = (
        analizar_lote(estados) if modo == "lote"
        else [analizar_mensaje(estado) for estado in estados]
    )
    assert len(resultados) == len(CASOS)
    diferencias = []
    for (identificador, _, esperado), resultado in zip(CASOS, resultados):
        assert not resultado.get("errores"), (identificador, resultado)
        analisis = AnalisisMensaje.model_validate(resultado)
        if analisis.es_spam_detectado is not esperado:
            diferencias.append((identificador, analisis.model_dump()))
        elif not esperado:
            assert analisis.motivo_spam is None
    assert not diferencias, diferencias
