"""Compara ejecuciones de referencia; Gemini solo se usa con --en-vivo."""

import argparse
import json
from pathlib import Path
from typing import cast

from src.agentes.estado_agente import EstadoAgente
from src.agentes.nodos.nodo_enrutador import determinar_rutas
from src.evaluacion import (
    CAMPOS_EVALUADOS,
    UMBRALES_MINIMOS,
    calcular_metricas,
    evaluacion_aprobada as _evaluacion_aprobada,
    evaluar_rutas_referencia,
)


RAIZ = Path(__file__).resolve().parents[1]
RUTA_REFERENCIA = RAIZ / "docs/evidencia2_entrega_ciencia_datos_completa.json"
RUTA_EJECUCION_ANTERIOR = RAIZ / "docs/evidencia_entrega_ciencia_datos_completa.json"
def cargar_interacciones(ruta: Path) -> list[dict]:
    with ruta.open("r", encoding="utf-8") as archivo:
        documento = json.load(archivo)
    interacciones = documento.get("interacciones")
    if not isinstance(interacciones, list):
        raise ValueError(f"{ruta}: falta la lista interacciones")
    return interacciones


def _analizar_en_vivo(referencias: list[dict]) -> list[dict]:
    from src.agentes.nodos.nodo_analizador import analizar_lote

    estados = [
        cast(EstadoAgente, {
            "id": caso["id"],
            "autor": caso.get("autor", ""),
            "canal": caso.get("canal", ""),
            "origen": caso.get("origen", ""),
            "idioma": caso.get("idioma", "es"),
            "texto": caso["texto"],
            "tipo_original": caso.get("tipo_original", ""),
            "score_relevancia": caso.get("score_relevancia"),
            "elegible_contenido": caso.get("elegible_contenido"),
            "elegible_faq": caso.get("elegible_faq", False),
        })
        for caso in referencias
    ]

    resultados = []
    for inicio in range(0, len(estados), 10):
        grupo = estados[inicio : inicio + 10]
        analisis = analizar_lote(grupo)
        for estado, campos in zip(grupo, analisis):
            resultado = cast(EstadoAgente, {**estado, **campos})
            resultado["rutas"] = (
                determinar_rutas(resultado)["rutas"]
                if not resultado.get("errores")
                else []
            )
            resultados.append(resultado)
    return resultados


def _imprimir_matriz_confusion(campo: str, matriz: dict) -> None:
    print("Matriz de confusión:")
    if campo == "rutas":
        print("ruta | TN | FP | FN | TP")
        for ruta, celdas in matriz.items():
            print(
                f"{ruta} | {celdas['negativo']['negativo']} | "
                f"{celdas['negativo']['positivo']} | "
                f"{celdas['positivo']['negativo']} | "
                f"{celdas['positivo']['positivo']}"
            )
        return

    etiquetas = list(matriz)
    print("real \\ predicha | " + " | ".join(etiquetas))
    for real in etiquetas:
        celdas = " | ".join(str(matriz[real][predicha]) for predicha in etiquetas)
        print(f"{real} | {celdas}")


def _imprimir_metricas(titulo: str, evaluacion: dict) -> bool:
    print(titulo)
    aprobado = _evaluacion_aprobada(evaluacion)
    for campo in CAMPOS_EVALUADOS:
        puntaje = evaluacion["metricas"][campo]
        umbral = UMBRALES_MINIMOS[campo]
        estado = "OK" if puntaje >= umbral else "ALERTA"
        print(f"{campo}: {puntaje:.1%} (mínimo {umbral:.0%}) [{estado}]")

    print("Métricas por clase (precisión / recall / F1 / soporte):")
    for campo, clases in evaluacion["metricas_por_clase"].items():
        print(f"{campo}:")
        for etiqueta, metricas_clase in clases.items():
            print(
                f"- {etiqueta}: "
                f"{metricas_clase['precision']:.1%} / "
                f"{metricas_clase['recall']:.1%} / "
                f"{metricas_clase['f1']:.1%} / "
                f"{metricas_clase['soporte']}"
            )
        _imprimir_matriz_confusion(
            campo,
            evaluacion["matrices_confusion"][campo],
        )

    if evaluacion["discrepancias"]:
        print("Discrepancias:")
        for diferencia in evaluacion["discrepancias"]:
            print(
                f"- {diferencia['id']} / {diferencia['campo']}: "
                f"esperado={diferencia['esperado']!r}, "
                f"obtenido={diferencia['obtenido']!r}"
            )
    return aprobado


def principal(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--en-vivo",
        action="store_true",
        help="Invoca Gemini y compara el análisis actual con la referencia.",
    )
    argumentos = parser.parse_args(argv)

    referencia = cargar_interacciones(RUTA_REFERENCIA)
    if argumentos.en_vivo:
        resultados = _analizar_en_vivo(referencia)
        evaluacion = calcular_metricas(referencia, resultados)
        aprobado = _imprimir_metricas("Evaluación actual contra referencia", evaluacion)
    else:
        anterior = cargar_interacciones(RUTA_EJECUCION_ANTERIOR)
        evaluacion = calcular_metricas(referencia, anterior)
        aprobado = _imprimir_metricas("Estabilidad entre ejecuciones guardadas", evaluacion)
        discrepancias_rutas = evaluar_rutas_referencia(referencia)
        if discrepancias_rutas:
            aprobado = False
            print("ALERTA: las rutas de referencia no coinciden con el enrutador actual:")
            for diferencia in discrepancias_rutas:
                print(
                    f"- {diferencia['id']}: esperado={diferencia['esperado']!r}, "
                    f"obtenido={diferencia['obtenido']!r}"
                )
        else:
            print(f"Rutas de referencia: {len(referencia)}/{len(referencia)} [OK]")

    return 0 if aprobado else 1


if __name__ == "__main__":
    raise SystemExit(principal())