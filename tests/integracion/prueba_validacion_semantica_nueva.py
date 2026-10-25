"""Ronda optativa congelada: consume cuota, sin reajuste ni escrituras cloud."""

import hashlib
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import pytest
from pydantic import ValidationError

from src.agentes.configuracion_ia import (
    TIER_ESTANDAR,
    obtener_modelo_nvidia_por_tier,
    obtener_proveedor_analisis,
)
from src.agentes.estado_agente import EstadoAgente
from src.agentes.modelos import AnalisisMensaje
from src.agentes.nodos.nodo_analizador import analizar_lote, analizar_mensaje


RAIZ = Path(__file__).resolve().parents[2]
ARCHIVO_MUESTRA = RAIZ / "tests" / "datos_validacion_semantica_nueva.json"
ARCHIVO_PROMPT = RAIZ / "src" / "agentes" / "prompts" / "analisis.py"
ARCHIVO_CONTRATO = RAIZ / "src" / "agentes" / "modelos.py"


def _huellas():
    return {
        "muestra": hashlib.sha256(ARCHIVO_MUESTRA.read_bytes()).hexdigest(),
        "prompt": hashlib.sha256(ARCHIVO_PROMPT.read_bytes()).hexdigest(),
        "contrato": hashlib.sha256(ARCHIVO_CONTRATO.read_bytes()).hexdigest(),
    }


@pytest.mark.parametrize("modo", ["lote", "individual"])
def test_muestra_nueva_sin_ajustar_expectativas(modo, tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="communitylab.ciencia_datos")
    huellas = _huellas()
    documento = json.loads(ARCHIVO_MUESTRA.read_text(encoding="utf-8"))
    casos = documento["casos"]
    inicio = datetime.now(timezone.utc).isoformat()
    proveedor = obtener_proveedor_analisis()
    modelo = obtener_modelo_nvidia_por_tier(TIER_ESTANDAR)
    resultados = []
    llamadas = []
    tamano = 10 if modo == "lote" else 1
    for posicion in range(0, len(casos), tamano):
        grupo = casos[posicion:posicion + tamano]
        estados: list[EstadoAgente] = [
            {"id": caso["id"], "texto": caso["texto"]} for caso in grupo
        ]
        reloj = perf_counter()
        salidas = (
            analizar_lote(estados) if modo == "lote"
            else [analizar_mensaje(estados[0])]
        )
        llamadas.append({
            "ids": [caso["id"] for caso in grupo],
            "segundos": perf_counter() - reloj,
        })
        assert len(salidas) == len(grupo)
        resultados.extend(salidas)

    evaluados = []
    for caso, salida in zip(casos, resultados):
        actual = None
        error_contrato = None
        if not salida.get("errores"):
            try:
                actual = AnalisisMensaje.model_validate(salida).model_dump()
            except ValidationError as error:
                error_contrato = str(error)
        diferencias = (
            {
                campo: {"admisibles": valores, "obtenido": actual[campo]}
                for campo, valores in caso["esperado"].items()
                if actual[campo] not in valores
            }
            if actual is not None else {}
        )
        evaluados.append({
            **caso,
            "resultado": actual,
            "errores": salida.get("errores", []),
            "error_contrato": error_contrato,
            "diferencias": diferencias,
            "concordante": actual is not None and not diferencias,
        })

    resumen_campos = {}
    for campo in ("tipo_detectado", "tema_principal", "es_spam_detectado"):
        aplicables = [caso for caso in evaluados if campo in caso["esperado"]]
        resumen_campos[campo] = {
            "evaluados": len(aplicables),
            "concordantes": sum(
                caso["resultado"] is not None
                and caso["resultado"][campo] in caso["esperado"][campo]
                for caso in aplicables
            ),
        }
    trazas = [
        record.campos for record in caplog.records
        if getattr(record, "evento", None) == "proveedor_ia_resuelto"
    ]
    reporte = {
        "inicio_utc": inicio,
        "fin_utc": datetime.now(timezone.utc).isoformat(),
        "modo": modo,
        "protocolo": documento["protocolo"],
        "huellas_antes": huellas,
        "huellas_despues": _huellas(),
        "proveedor_configurado": proveedor,
        "modelo_nvidia_configurado": modelo,
        "resoluciones_proveedor": trazas,
        "eventos_operativos": [
            {
                "evento": record.evento,
                **{
                    clave: valor for clave, valor in record.campos.items()
                    if clave in {
                        "id_interaccion", "ids_interaccion", "etapa", "intento",
                        "intentos", "espera_segundos", "tipo_error",
                        "duracion_ms", "modelo",
                    }
                },
            }
            for record in caplog.records
            if getattr(record, "evento", None) in {
                "llm_fin", "llm_error", "reintento_programado", "operacion_fallida",
            }
        ],
        "llamadas": llamadas,
        "resumen": {
            "casos": len(evaluados),
            "concordantes": sum(caso["concordante"] for caso in evaluados),
            "por_campo": resumen_campos,
            "grupos": dict(Counter(caso["grupo"] for caso in evaluados)),
        },
        "casos": evaluados,
    }
    archivo = tmp_path / f"validacion_nueva_{modo}.json"
    archivo.write_text(json.dumps(reporte, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Evaluacion guardada: {archivo}")
    assert reporte["huellas_despues"] == huellas, "La ronda no permite modificar instrucciones ni etiquetas"
    fallos = [caso["id"] for caso in evaluados if not caso["concordante"]]
    assert not fallos, f"Discrepancias sin reajuste: {fallos}; evidencia: {archivo}"
