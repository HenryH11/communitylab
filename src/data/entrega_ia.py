"""Prepara población, estados y plan de entrega; no llama a IA ni escribe archivos."""

from .ingest import (
    _interaccion_para_entrega, construir_estados_agente, procesar_datos,
    validar_tamano_ciclo, validar_y_limpiar,
)


CAMPOS = ("id", "autor", "canal", "tipo", "texto", "fecha", "idioma")
EXCLUSIONES_CALIDAD = {"solo_enlaces", "texto_repetitivo", "contenido_eliminado", "duplicado"}


def _lotes(datos):
    return datos["lotes"] if "lotes" in datos else [datos]


def _validar_identidad_y_contexto(datos):
    vistos = set()
    for i, lote in enumerate(_lotes(datos)):
        for j, mensaje in enumerate(lote["interacciones"]):
            ruta = f"lotes[{i}].interacciones[{j}]"
            try:
                # El vacío se excluye por calidad, pero se valida su contexto.
                _interaccion_para_entrega(mensaje, permitir_texto_vacio=True)
            except ValueError as error:
                raise ValueError(f"{ruta}: {error}") from error
            if mensaje["id"] in vistos:
                raise ValueError(f"{ruta}.id: debe ser único en la entrega")
            vistos.add(mensaje["id"])


def _proyectar_lote(lote, mensajes):
    return {
        "origen_comunidad": lote["origen_comunidad"],
        "periodo_referencia": lote["periodo_referencia"],
        "interacciones": [{campo: m[campo] for campo in CAMPOS} for m in mensajes],
    }


def preparar_entrega(datos, *, fecha_referencia, config=None):
    """Devuelve completos, contenido e informe sin mutar la entrada.

    Conserva críticas breves, bajo puntaje y mensajes fuera del top_n para
    sentimiento. Solo excluye ruido/duplicación documentados. Requiere IDs
    globales únicos y metadatos válidos para esta entrega.
    """
    limpios = validar_y_limpiar(datos)
    _validar_identidad_y_contexto(limpios)
    seleccion, informe = procesar_datos(limpios, fecha_referencia=fecha_referencia, config=config)
    completos = {"lotes": []}
    contenido = {"lotes": []}
    informe["version_entrega"] = "1.1-propuesta"
    informe["resumen_sentimiento"] = {"total": informe["resumen"]["total"], "incluidas": 0, "excluidas_calidad": 0}
    for lote, lote_seleccion, revision in zip(_lotes(limpios), _lotes(seleccion), informe["lotes"]):
        validos = []
        for mensaje, evaluacion in zip(lote["interacciones"], revision["evaluaciones"]):
            motivos = sorted(EXCLUSIONES_CALIDAD.intersection(evaluacion["motivos"]))
            if not mensaje["texto"]:
                motivos.append("texto_vacio")
            evaluacion["incluido_sentimiento"] = not motivos
            evaluacion["motivos_exclusion_sentimiento"] = motivos
            if not motivos:
                validos.append(mensaje)
        completos["lotes"].append(_proyectar_lote(lote, validos))
        contenido["lotes"].append(_proyectar_lote(lote_seleccion, lote_seleccion["interacciones"]))
        informe["resumen_sentimiento"]["incluidas"] += len(validos)
    resumen = informe["resumen_sentimiento"]
    resumen["excluidas_calidad"] = resumen["total"] - resumen["incluidas"]
    return completos, contenido, informe


def construir_plan_procesamiento(estados, tamano_ciclo=20):
    """Plan por IDs: ciclos de 10 a N y remanentes explícitos pendientes.

    Agrupa estados de distintos orígenes; cada estado conserva su propio origen.
    Reequilibra cuando es posible, sin rellenar ni duplicar. No ejecuta el grafo
    ni controla la frecuencia de llamadas al LLM.
    """
    validar_tamano_ciclo(tamano_ciclo)
    ids = [e.get("id") for e in estados]
    if any(not isinstance(i, str) or not i.strip() or i != i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("El plan requiere IDs únicos y no vacíos")
    cantidad = len(ids)
    numero_ciclos = (cantidad + tamano_ciclo - 1) // tamano_ciclo
    tamanos = []
    if numero_ciclos and cantidad >= 10 * numero_ciclos:
        base, extra = divmod(cantidad, numero_ciclos)
        tamanos = [base + (i < extra) for i in range(numero_ciclos)]
    elif cantidad:
        tamanos = [tamano_ciclo] * (cantidad // tamano_ciclo)
    ciclos = []
    inicio = 0
    for indice, tamano in enumerate(tamanos):
        ciclos.append({"indice": indice, "cantidad": tamano, "ids": ids[inicio:inicio + tamano]})
        inicio += tamano
    return {
        "minimo": 10, "maximo": tamano_ciclo, "total": cantidad,
        "ciclos": ciclos, "pendientes": ids[inicio:],
        "motivo_pendientes": "No alcanza el mínimo de 10; conservar para el próximo ciclo" if inicio < cantidad else None,
    }


def preparar_paquete_ia(datos, *, fecha_referencia, config=None, tamano_ciclo=20):
    """Reutiliza el adaptador de Gustavo; elegibilidad separada de AgentState."""
    completos, contenido, informe = preparar_entrega(datos, fecha_referencia=fecha_referencia, config=config)
    estados = construir_estados_agente(completos, informe, poblacion="sentimiento")
    plan = construir_plan_procesamiento(estados, tamano_ciclo)
    plan["ids_contenido"] = [m["id"] for lote in contenido["lotes"] for m in lote["interacciones"]]
    return {
        "completos": completos, "contenido": contenido, "informe": informe,
        "estados": estados, "plan": plan,
    }
