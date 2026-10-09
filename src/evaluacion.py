"""Métricas y validaciones para la evaluación de regresión de Data Science."""

from typing import cast

from src.agentes.estado_agente import EstadoAgente
from src.agentes.nodos.nodo_enrutador import determinar_rutas


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


def _normalizar(valor, campo):
    if campo == "rutas":
        return tuple(sorted(valor)) if isinstance(valor, list) else None
    return valor


def _metricas_binarias(verdaderos_positivos, falsos_positivos, falsos_negativos, soporte):
    precision = (
        verdaderos_positivos / (verdaderos_positivos + falsos_positivos)
        if verdaderos_positivos + falsos_positivos
        else 0.0
    )
    positivos_reales = verdaderos_positivos + falsos_negativos
    recall = verdaderos_positivos / positivos_reales if positivos_reales else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "soporte": soporte,
    }


def _valor_clasificacion(interaccion: dict, campo: str):
    valor = interaccion.get(campo)
    return valor if valor is not None else "<sin_prediccion>"


def _metricas_categoricas(referencias_por_id: dict, predicciones_por_id: dict, campo: str):
    etiquetas = sorted(
        {
            _valor_clasificacion(referencia, campo)
            for referencia in referencias_por_id.values()
        }
        | {
            _valor_clasificacion(predicciones_por_id.get(identificador, {}), campo)
            for identificador in referencias_por_id
        }
    )
    matriz = {real: {predicha: 0 for predicha in etiquetas} for real in etiquetas}

    for identificador, referencia in referencias_por_id.items():
        real = _valor_clasificacion(referencia, campo)
        predicha = _valor_clasificacion(
            predicciones_por_id.get(identificador, {}), campo
        )
        matriz[real][predicha] += 1

    por_clase = {}
    for etiqueta in etiquetas:
        soporte = sum(matriz[etiqueta].values())
        verdaderos_positivos = matriz[etiqueta][etiqueta]
        falsos_positivos = sum(
            matriz[real][etiqueta]
            for real in etiquetas
            if real != etiqueta
        )
        falsos_negativos = soporte - verdaderos_positivos
        por_clase[etiqueta] = _metricas_binarias(
            verdaderos_positivos,
            falsos_positivos,
            falsos_negativos,
            soporte,
        )
    return por_clase, matriz


def _metricas_rutas(referencias_por_id: dict, predicciones_por_id: dict):
    conjuntos_reales = {}
    conjuntos_predichos = {}
    etiquetas = set()
    for identificador, referencia in referencias_por_id.items():
        rutas_reales = set(referencia.get("rutas") or [])
        rutas_predichas = set(
            predicciones_por_id.get(identificador, {}).get("rutas") or []
        )
        conjuntos_reales[identificador] = rutas_reales
        conjuntos_predichos[identificador] = rutas_predichas
        etiquetas.update(rutas_reales)
        etiquetas.update(rutas_predichas)

    por_clase = {}
    matrices = {}
    total = len(referencias_por_id)
    for etiqueta in sorted(etiquetas):
        verdaderos_positivos = sum(
            etiqueta in conjuntos_reales[identificador]
            and etiqueta in conjuntos_predichos[identificador]
            for identificador in referencias_por_id
        )
        falsos_positivos = sum(
            etiqueta not in conjuntos_reales[identificador]
            and etiqueta in conjuntos_predichos[identificador]
            for identificador in referencias_por_id
        )
        falsos_negativos = sum(
            etiqueta in conjuntos_reales[identificador]
            and etiqueta not in conjuntos_predichos[identificador]
            for identificador in referencias_por_id
        )
        verdaderos_negativos = total - verdaderos_positivos - falsos_positivos - falsos_negativos
        soporte = verdaderos_positivos + falsos_negativos
        por_clase[etiqueta] = _metricas_binarias(
            verdaderos_positivos,
            falsos_positivos,
            falsos_negativos,
            soporte,
        )
        matrices[etiqueta] = {
            "negativo": {
                "negativo": verdaderos_negativos,
                "positivo": falsos_positivos,
            },
            "positivo": {
                "negativo": falsos_negativos,
                "positivo": verdaderos_positivos,
            },
        }
    return por_clase, matrices


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
        for identificador in sorted(ids_inesperados, key=str)
    )

    metricas_por_clase = {}
    matrices_confusion = {}
    for campo in CAMPOS_EVALUADOS:
        if campo == "rutas":
            metricas_por_clase[campo], matrices_confusion[campo] = _metricas_rutas(
                referencias_por_id,
                predicciones_por_id,
            )
        else:
            metricas_por_clase[campo], matrices_confusion[campo] = _metricas_categoricas(
                referencias_por_id,
                predicciones_por_id,
                campo,
            )

    return {
        "metricas": metricas,
        "metricas_por_clase": metricas_por_clase,
        "matrices_confusion": matrices_confusion,
        "discrepancias": discrepancias,
    }


def evaluar_rutas_referencia(interacciones: list[dict]) -> list[dict]:
    """Comprueba que las etiquetas de referencia produzcan las rutas esperadas."""
    discrepancias = []
    for interaccion in interacciones:
        estado = cast(EstadoAgente, {
            "tipo_detectado": interaccion.get("tipo_detectado"),
            "sentimiento": interaccion.get("sentimiento"),
            "score_relevancia": interaccion.get("score_relevancia"),
            "elegible_contenido": interaccion.get("elegible_contenido"),
            "elegible_faq": interaccion.get("elegible_faq", False),
        })
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


def evaluacion_aprobada(evaluacion: dict) -> bool:
    """Aplica umbrales mínimos y rechaza IDs inesperados."""
    if any(
        discrepancia["campo"] == "id"
        for discrepancia in evaluacion["discrepancias"]
    ):
        return False
    return all(
        evaluacion["metricas"].get(campo, 0) >= umbral
        for campo, umbral in UMBRALES_MINIMOS.items()
    )