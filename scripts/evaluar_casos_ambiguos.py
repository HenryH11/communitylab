"""Compara ejecuciones de referencia; Gemini solo se usa con --en-vivo."""

import argparse
import json
from pathlib import Path

from src.agentes.nodos.nodo_enrutador import determinar_rutas


RAIZ = Path(__file__).resolve().parents[1]
RUTA_REFERENCIA = RAIZ / "docs/evidencia2_entrega_ciencia_datos_completa.json"
RUTA_EJECUCION_ANTERIOR = RAIZ / "docs/evidencia_entrega_ciencia_datos_completa.json"
CAMPOS_EVALUADOS = (
    "sentimiento",
    "tema_principal",
    "tipo_detectado",
    "rutas",
)
UMBRALES_MINIMOS = {
    "sentimiento": 0.80,
    "tema_principal": 0.80,
    "tipo_detectado": 0.80,
    "rutas": 0.75,
}


def cargar_interacciones(ruta: Path) -> list[dict]:
    with ruta.open("r", encoding="utf-8") as archivo:
        documento = json.load(archivo)
    interacciones = documento.get("interacciones")
    if not isinstance(interacciones, list):
        raise ValueError(f"{ruta}: falta la lista interacciones")
    return interacciones


def _normalizar(valor, campo):
    if campo == "rutas":
        return tuple(sorted(valor)) if isinstance(valor, list) else None
    return valor


def calcular_metricas(referencias: list[dict], predicciones: list[dict]) -> dict:
    """Calcula coincidencia exacta por dimensión e informa discrepancias por ID."""
    referencias_por_id = {caso.get("id"): caso for caso in referencias}
    predicciones_por_id = {caso.get("id"): caso for caso in predicciones}
    if (
        None in referencias_por_id
        or None in predicciones_por_id
        or len(referencias_por_id) != len(referencias)
        or len(predicciones_por_id) != len(predicciones)
    ):
        raise ValueError("Cada interacción evaluada requiere un ID único")

    discrepancias = []
    metricas = {}
    for campo in CAMPOS_EVALUADOS:
        aciertos = 0
        for identificador, esperado in referencias_por_id.items():
            obtenido = predicciones_por_id.get(identificador, {})
            coincide = _normalizar(esperado.get(campo), campo) == _normalizar(
                obtenido.get(campo), campo
            )
            aciertos += coincide
            if not coincide:
                discrepancias.append(
                    {
                        "id": identificador,
                        "campo": campo,
                        "esperado": esperado.get(campo),
                        "obtenido": obtenido.get(campo),
                    }
                )
        metricas[campo] = aciertos / len(referencias_por_id) if referencias_por_id else 1.0

    ids_inesperados = set(predicciones_por_id) - set(referencias_por_id)
    discrepancias.extend(
        {"id": identificador, "campo": "id", "esperado": None, "obtenido": "inesperado"}
        for identificador in sorted(ids_inesperados)
    )
    return {"metricas": metricas, "discrepancias": discrepancias}


def evaluar_rutas_referencia(interacciones: list[dict]) -> list[dict]:
    """Comprueba que las etiquetas de referencia produzcan las rutas esperadas."""
    discrepancias = []
    for interaccion in interacciones:
        estado = {
            "tipo_detectado": interaccion.get("tipo_detectado"),
            "sentimiento": interaccion.get("sentimiento"),
            "score_relevancia": interaccion.get("score_relevancia"),
            "elegible_contenido": interaccion.get("elegible_contenido"),
            "elegible_faq": interaccion.get("elegible_faq", False),
        }
        rutas = determinar_rutas(estado)["rutas"]
        if _normalizar(interaccion.get("rutas"), "rutas") != _normalizar(
            rutas, "rutas"
        ):
            discrepancias.append(
                {
                    "id": interaccion.get("id"),
                    "campo": "rutas",
                    "esperado": interaccion.get("rutas"),
                    "obtenido": rutas,
                }
            )
    return discrepancias


def _analizar_en_vivo(referencias: list[dict]) -> list[dict]:
    from src.agentes.nodos.nodo_analizador import analizar_lote

    estados = [
        {
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
        }
        for caso in referencias
    ]

    resultados = []
    for inicio in range(0, len(estados), 10):
        grupo = estados[inicio : inicio + 10]
        analisis = analizar_lote(grupo)
        for estado, campos in zip(grupo, analisis):
            resultado = {**estado, **campos}
            resultado["rutas"] = (
                determinar_rutas(resultado)["rutas"]
                if not resultado.get("errores")
                else []
            )
            resultados.append(resultado)
    return resultados


def _imprimir_metricas(titulo: str, evaluacion: dict) -> bool:
    print(titulo)
    aprobado = _evaluacion_aprobada(evaluacion)
    for campo in CAMPOS_EVALUADOS:
        puntaje = evaluacion["metricas"][campo]
        umbral = UMBRALES_MINIMOS[campo]
        estado = "OK" if puntaje >= umbral else "ALERTA"
        print(f"{campo}: {puntaje:.1%} (mínimo {umbral:.0%}) [{estado}]")

    if evaluacion["discrepancias"]:
        print("Discrepancias:")
        for diferencia in evaluacion["discrepancias"]:
            print(
                f"- {diferencia['id']} / {diferencia['campo']}: "
                f"esperado={diferencia['esperado']!r}, "
                f"obtenido={diferencia['obtenido']!r}"
            )
    return aprobado


def _evaluacion_aprobada(evaluacion: dict) -> bool:
    if any(
        discrepancia["campo"] == "id"
        for discrepancia in evaluacion["discrepancias"]
    ):
        return False
    return all(
        evaluacion["metricas"].get(campo, 0) >= umbral
        for campo, umbral in UMBRALES_MINIMOS.items()
    )


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