"""Evaluación optativa de muestra y controles; consume cuota, sin escrituras cloud."""

import json

import pytest

from src.agentes.estado_agente import EstadoAgente
from src.agentes.modelos import AnalisisMensaje
from src.agentes.nodos.nodo_analizador import analizar_lote, analizar_mensaje
from tests.casos_semanticos_regresion import casos_semanticos


@pytest.mark.parametrize("modo", ["lote", "individual"])
def test_tipos_y_temas_de_muestra_y_controles(modo, tmp_path):
    casos = casos_semanticos()
    resultados = []
    for inicio in range(0, len(casos), 10):
        grupo = casos[inicio:inicio + 10]
        estados: list[EstadoAgente] = [
            {"id": identificador, "texto": texto} for identificador, texto, _ in grupo
        ]
        analisis = (
            analizar_lote(estados) if modo == "lote"
            else [analizar_mensaje(estado) for estado in estados]
        )
        assert len(analisis) == len(grupo)
        resultados.extend(analisis)
    diferencias = []
    evaluados = []
    for (identificador, texto, esperado), resultado in zip(casos, resultados):
        assert not resultado.get("errores"), (identificador, resultado)
        actual = AnalisisMensaje.model_validate(resultado).model_dump()
        discrepancias = {
            campo: {"esperado": valor, "obtenido": actual[campo]}
            for campo, valor in esperado.items() if actual[campo] != valor
        }
        cambios = {
            campo: valores for campo, valores in discrepancias.items()
            if campo != "sentimiento"
        }
        evaluados.append({
            "id": identificador, "texto": texto, "esperado_parcial": esperado,
            "resultado": actual, "diferencias": cambios,
            "observaciones_sentimiento": {
                campo: valores for campo, valores in discrepancias.items()
                if campo == "sentimiento"
            },
        })
        if cambios:
            diferencias.append({"id": identificador, "diferencias": cambios})
    archivo = tmp_path / f"evaluacion_semantica_{modo}.json"
    archivo.write_text(json.dumps(evaluados, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"Evaluacion guardada: {archivo}")
    assert not diferencias, diferencias
