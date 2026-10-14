"""Lectura, validación, limpieza y selección de JSON para el flujo de IA."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from src.agentes.estado_agente import EstadoAgente

if __package__:
    from .relevancia import TIPOS, ConfiguracionRelevancia, leer_fecha, seleccionar_lote
    from .limpieza import (
        ETIQUETAS,
        _CATEGORIAS_CONTROL,
        _texto_visible,
        caracteres_especiales_preservados,
        contar_caracteres_no_ascii,
        detectar_mojibake,
        estimar_tokens,
        limpiar_texto,
        reparar_mojibake,
    )
    from .ciclos_transporte import (
        _CAMPOS_CONTRATO_NELSON,
        _CARACTERES_NO_SEGUROS_ARCHIVO,
        _interaccion_para_entrega,
        _nombre_seguro,
        construir_ciclos,
        guardar_ciclos,
        validar_destino_ciclos,
        validar_tamano_ciclo,
    )
else:
    from relevancia import TIPOS, ConfiguracionRelevancia, leer_fecha, seleccionar_lote
    from limpieza import (
        ETIQUETAS,
        _CATEGORIAS_CONTROL,
        _texto_visible,
        caracteres_especiales_preservados,
        contar_caracteres_no_ascii,
        detectar_mojibake,
        estimar_tokens,
        limpiar_texto,
        reparar_mojibake,
    )
    from ciclos_transporte import (
        _CAMPOS_CONTRATO_NELSON,
        _CARACTERES_NO_SEGUROS_ARCHIVO,
        _interaccion_para_entrega,
        _nombre_seguro,
        construir_ciclos,
        guardar_ciclos,
        validar_destino_ciclos,
        validar_tamano_ciclo,
    )


RAIZ = Path(__file__).resolve().parents[2]


def _cadena(objeto, campo, ruta, vacia=False):
    valor = objeto.get(campo)
    if not isinstance(valor, str) or (not vacia and not valor.strip()):
        raise ValueError(f"{ruta}.{campo}: se esperaba texto" + (" no vacío" if not vacia else ""))
    try:
        valor.encode("utf-8", errors="strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"{ruta}.{campo}: texto no representable en UTF-8") from error


def validar_y_limpiar(datos):
    """Acepta un lote oficial o {metadata, lotes: [...]}; falla ante esquema inválido."""
    if not isinstance(datos, dict):
        raise ValueError("La raíz debe ser un objeto JSON")
    resultado = deepcopy(datos)
    if "lotes" in resultado:
        if any(c in resultado for c in ("origen_comunidad", "periodo_referencia", "interacciones")):
            raise ValueError("No mezclar un lote individual con el contenedor lotes")
        lotes = resultado["lotes"]
        if not isinstance(lotes, list):
            raise ValueError("lotes debe ser una lista")
        if "metadata" in resultado and not isinstance(resultado["metadata"], dict):
            raise ValueError("metadata debe ser un objeto")
    else:
        lotes = [resultado]
    for indice, lote in enumerate(lotes):
        ruta = f"lotes[{indice}]"
        if not isinstance(lote, dict):
            raise ValueError(f"{ruta}: se esperaba un objeto")
        for campo in ("origen_comunidad", "periodo_referencia"):
            _cadena(lote, campo, ruta)
        if not isinstance(lote.get("interacciones"), list):
            raise ValueError(f"{ruta}.interacciones: se esperaba una lista")
        for numero, mensaje in enumerate(lote["interacciones"]):
            ubicacion = f"{ruta}.interacciones[{numero}]"
            if not isinstance(mensaje, dict):
                raise ValueError(f"{ubicacion}: se esperaba un objeto")
            for campo in ("autor", "canal", "tipo", "texto"):
                _cadena(mensaje, campo, ubicacion, vacia=campo == "texto")
            if mensaje["tipo"] not in TIPOS:
                raise ValueError(f"{ubicacion}.tipo: valor no admitido")
            for campo in ("id", "fecha", "idioma"):
                if campo in mensaje:
                    _cadena(mensaje, campo, ubicacion)
            for campo in ("autor", "canal", "texto"):
                mensaje[campo] = limpiar_texto(mensaje[campo])
            for campo in ("autor", "canal"):
                _cadena(mensaje, campo, ubicacion)
    return resultado


def actualizar_totales_rendimiento(rendimiento):
    """Suma cada población sin interpretar una medición ausente como cero."""
    for campo in (
        "caracteres_entrada", "caracteres_limpios", "caracteres_contenido",
        "tokens_estimados_contenido", "interacciones_analisis",
        "caracteres_analisis", "tokens_estimados_analisis",
    ):
        valores = [lote[campo] for lote in rendimiento["lotes"]]
        rendimiento[campo + "_total"] = (
            sum(valores) if all(v is not None for v in valores) else None
        )
    if not rendimiento["analisis_disponible"]:
        for campo in ("interacciones_analisis", "caracteres_analisis", "tokens_estimados_analisis"):
            rendimiento[campo + "_total"] = None
    # Alias de Gustavo: sigue midiendo exclusivamente candidatos para contenido.
    rendimiento["tokens_estimados_total"] = rendimiento["tokens_estimados_contenido_total"]


def procesar_datos(datos, *, fecha_referencia, configuracion=None):
    """Devuelve (datos seleccionados, informe). No modifica datos ni usa red/reloj."""
    configuracion = configuracion if configuracion is not None else ConfiguracionRelevancia()
    if isinstance(fecha_referencia, str):
        fecha_referencia = leer_fecha(fecha_referencia)
    if not isinstance(fecha_referencia, datetime) or fecha_referencia.tzinfo is None:
        raise ValueError("fecha_referencia debe incluir zona horaria")
    salida = validar_y_limpiar(datos)
    lotes = salida["lotes"] if "lotes" in salida else [salida]
    lotes_originales = datos["lotes"] if "lotes" in datos else [datos]
    informe = {
        "version_criterio": "1.0-propuesta",
        "fecha_referencia": fecha_referencia.astimezone(timezone.utc).isoformat(),
        "configuracion": configuracion.como_dict(),
        "resumen": {"total": 0, "seleccionadas": 0, "descartadas": 0},
        "lotes": [],
    }
    rendimiento_lotes = []
    for indice, lote in enumerate(lotes):
        originales = lotes_originales[indice]["interacciones"]
        interacciones = lote["interacciones"]
        alertas = [numero for numero, (original, limpio) in enumerate(zip(originales, interacciones))
                   if not caracteres_especiales_preservados(original["texto"], limpio["texto"])]
        seleccionadas, evaluaciones = seleccionar_lote(lote, configuracion, fecha_referencia)
        # Estimación de texto candidato. El paquete completo mide análisis aparte.
        tokens_estimados = sum(estimar_tokens(m["texto"]) for m in seleccionadas)
        lote["interacciones"] = seleccionadas
        informe["lotes"].append({
            "indice": indice, "origen_comunidad": lote["origen_comunidad"],
            "periodo_referencia": lote["periodo_referencia"], "evaluaciones": evaluaciones,
        })
        informe["resumen"]["total"] += len(evaluaciones)
        informe["resumen"]["seleccionadas"] += len(seleccionadas)
        rendimiento_lotes.append({
            "indice": indice,
            "origen_comunidad": informe["lotes"][-1]["origen_comunidad"],
            "interacciones_seleccionadas": len(seleccionadas),
            "tokens_estimados": tokens_estimados,
            "caracteres_especiales_preservados": not alertas,
            "interacciones_con_alerta_caracteres": alertas,
            "caracteres_entrada": sum(len(m["texto"]) for m in originales),
            "caracteres_limpios": sum(len(m["texto"]) for m in interacciones),
            "caracteres_contenido": sum(len(m["texto"]) for m in seleccionadas),
            "tokens_estimados_contenido": tokens_estimados,
            "interacciones_analisis": None,
            "caracteres_analisis": None,
            "tokens_estimados_analisis": None,
        })
    informe["resumen"]["descartadas"] = informe["resumen"]["total"] - informe["resumen"]["seleccionadas"]
    # Deliberadamente sin tiempos de reloj aquí: procesar_datos debe seguir siendo
    # reproducible byte a byte (ver PruebasSeleccion.test_reproducible_con_referencia_fija
    # y PruebasIntegracion.test_cli_tamano_ciclo_es_opt_in_no_cambia_la_salida_por_defecto).
    # La latencia se mide en principal(), al nivel del CLI, no aquí.
    informe["rendimiento"] = {
        "version": "1.1",
        "unidad_caracteres": "puntos_de_codigo_unicode",
        "metodo_tokens": "aproximacion_caracteres_4",
        "alcance_tokens": "Solo texto; excluye prompts, metadatos, respuestas y reintentos",
        "analisis_disponible": False,
        "lotes_con_alerta_caracteres": [r["indice"] for r in rendimiento_lotes if not r["caracteres_especiales_preservados"]],
        "lotes": rendimiento_lotes,
    }
    actualizar_totales_rendimiento(informe["rendimiento"])
    return salida, informe


def construir_estado_agente(
    mensaje,
    puntaje,
    origen,
    elegible_faq=False,
) -> "EstadoAgente":
    """Traduce una interacción ya depurada al subconjunto de entrada de `EstadoAgente`
    (ver `src/agentes/estado_agente.py`, Sub-equipo 2), confirmado con Ciencia de Datos:

    - `autor`, `canal`, `texto`: sin cambios.
    - `tipo` no se modifica ni se renombra; se copia (no se reemplaza) hacia
    `tipo_original`, que Ciencia de Datos usa para comparar contra su propia
      clasificación posterior.
    - `puntaje` (de `relevancia.py`) se expone como `score_relevancia`.
    - `origen` viene de `origen_comunidad` del lote, bajado a nivel de interacción.
    - `id`/`idioma` se incluyen solo si la interacción los trae (son opcionales en
      el contrato); no se fabrica ningún valor por defecto.
    - `elegible_faq` viene de `relevancia.py` (pregunta completa del programa con
      score suficiente). Es un campo para Ciencia de Datos; no cruza el contrato de
      entrega de Nelson, que mantiene sus siete campos.

    No incluye campos que produce Ciencia de Datos (`sentimiento`, `rutas`,
    `activos_generados`, etc.) — esos se agregan más adelante en su propio grafo.
    """
    estado = {
        "autor": mensaje["autor"],
        "canal": mensaje["canal"],
        "origen": origen,
        "texto": mensaje["texto"],
        "tipo_original": mensaje["tipo"],
        "score_relevancia": puntaje,
        "elegible_faq": elegible_faq,
    }
    for campo in ("id", "idioma"):
        if campo in mensaje:
            estado[campo] = mensaje[campo]
    return cast("EstadoAgente", estado)


def construir_estados_agente(salida, informe, *, poblacion="contenido"):
    """Mapea por ID, conserva el orden recibido y exige la población completa.

    `contenido` usa seleccionado; `sentimiento` usa incluido_sentimiento del
    informe de preparar_entrega. No empareja por posición ni recalcula puntajes.
    """
    if poblacion not in {"contenido", "sentimiento"}:
        raise ValueError("poblacion debe ser contenido o sentimiento")
    campo = "seleccionado" if poblacion == "contenido" else "incluido_sentimiento"
    evaluaciones = {}
    for lote in informe["lotes"]:
        for evaluacion in lote["evaluaciones"]:
            identificador = evaluacion.get("id")
            if not isinstance(identificador, str) or not identificador.strip() or identificador != identificador.strip():
                raise ValueError("El mapeo requiere IDs no vacíos y sin espacios exteriores")
            if identificador in evaluaciones or campo not in evaluacion:
                raise ValueError("Informe con IDs repetidos o población sin definir")
            evaluaciones[identificador] = (lote, evaluacion)
    esperados = {k for k, (_, e) in evaluaciones.items() if e[campo]}
    recibidos = set()
    estados = []
    datos = validar_y_limpiar(salida)
    for lote in datos["lotes"] if "lotes" in datos else [datos]:
        for interaccion in lote["interacciones"]:
            identificador = interaccion.get("id")
            if identificador in recibidos or identificador not in esperados:
                raise ValueError("Los IDs de la entrega y el informe no coinciden")
            recibidos.add(identificador)
            contexto, evaluacion = evaluaciones[identificador]
            if any(lote[c] != contexto[c] for c in ("origen_comunidad", "periodo_referencia")):
                raise ValueError(f"Contexto incompatible para {identificador}")
            estados.append(construir_estado_agente(
                interaccion, evaluacion["puntaje"], lote["origen_comunidad"],
                elegible_faq=evaluacion["elegible_faq"],
            ))
    if recibidos != esperados:
        raise ValueError("Faltan IDs de la población indicada por el informe")
    return estados


def cargar_json(ruta):
    with Path(ruta).open(encoding="utf-8-sig") as archivo:
        return json.load(archivo)


def guardar_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def principal(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=RAIZ / "src/datos/mensajes_comunidad_simulados.json")
    parser.add_argument("--salida", type=Path, default=RAIZ / "salida/datos/mensajes_filtrados.json")
    parser.add_argument("--informe", type=Path, default=RAIZ / "salida/datos/informe_relevancia.json")
    parser.add_argument(
        "--registro-rendimiento", type=Path,
        help="JSON opcional de ejecución con tiempo y métricas, separado del informe reproducible",
    )
    parser.add_argument(
        "--configuracion",
        dest="configuracion",
        type=Path,
        help="Archivo JSON con parámetros de relevancia",
    )
    parser.add_argument(
        "--config",
        dest="configuracion",
        type=Path,
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--fecha-referencia", help="ISO 8601 con zona; por defecto, instante actual UTC")
    parser.add_argument(
        "--maximo-por-lote",
        dest="maximo_por_lote",
        type=int,
        help="Máximo de mensajes por lote tras aplicar el umbral",
    )
    parser.add_argument(
        "--top-n",
        dest="maximo_por_lote",
        type=int,
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--puntaje-minimo",
        dest="puntaje_minimo",
        type=int,
        help="Umbral de selección de 0 a 100",
    )
    parser.add_argument(
        "--min-puntaje",
        dest="puntaje_minimo",
        type=int,
        default=argparse.SUPPRESS,
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--tamano-ciclo", type=int, help="Máximo N entre 10 y 30 para fragmentos y plan de entrega; activa archivos por origen")
    parser.add_argument("--ciclos", type=Path, default=RAIZ / "salida/datos/entregas", help="Directorio de fragmentos por ciclo; se usa junto con --tamano-ciclo")
    parser.add_argument(
        "--entrega-ia",
        type=Path,
        metavar="CARPETA",
        help="Exporta la población completa, los estados y el plan de ciclos sin llamar a IA",
    )
    argumentos = parser.parse_args(argv)
    try:
        salidas = [argumentos.salida.resolve(), argumentos.informe.resolve()]
        if argumentos.registro_rendimiento is not None:
            salidas.append(argumentos.registro_rendimiento.resolve())
        adicionales = []
        if argumentos.entrega_ia is not None:
            adicionales = [argumentos.entrega_ia / nombre for nombre in (
                "mensajes_limpios_completos.json", "estados_agente.json", "plan_procesamiento.json",
            )]
            salidas.extend(p.resolve() for p in adicionales)
        entradas = [argumentos.entrada.resolve()] + ([argumentos.configuracion.resolve()] if argumentos.configuracion else [])
        if len(set(salidas)) != len(salidas) or any(p in entradas for p in salidas):
            raise ValueError("Entrada, configuración, salida e informe deben usar archivos distintos")
        if any(p.exists() and not p.is_file() for p in salidas):
            raise ValueError("Una salida coincide con un directorio")
        if any(p in q.parents for p in salidas + entradas for q in salidas):
            raise ValueError("Un archivo no puede usarse como directorio de salida")
        if argumentos.tamano_ciclo is not None:
            validar_tamano_ciclo(argumentos.tamano_ciclo)
            ciclos_resuelto = argumentos.ciclos.resolve()
            if any(p == ciclos_resuelto or ciclos_resuelto in p.parents for p in entradas + salidas):
                raise ValueError("--ciclos no puede coincidir con la entrada, configuración, salida o informe")
        opciones = cargar_json(argumentos.configuracion) if argumentos.configuracion else {}
        if not isinstance(opciones, dict):
            raise ValueError("La configuración debe ser un objeto JSON")
        for campo in ("maximo_por_lote", "puntaje_minimo"):
            if getattr(argumentos, campo) is not None:
                opciones[campo] = getattr(argumentos, campo)
        configuracion = ConfiguracionRelevancia(**opciones)
        referencia = argumentos.fecha_referencia or datetime.now(timezone.utc).isoformat()
        datos = cargar_json(argumentos.entrada)
        paquete = None
        tiempo_procesamiento_inicio = time.perf_counter()
        if argumentos.entrega_ia is not None:
            if not __package__:
                import sys
                sys.path.insert(0, str(RAIZ))
            from src.datos.entrega_ia import preparar_paquete_ia
            paquete = preparar_paquete_ia(datos, fecha_referencia=referencia, configuracion=configuracion,
                                          tamano_ciclo=argumentos.tamano_ciclo if argumentos.tamano_ciclo is not None else 20)
            salida, informe = paquete["contenido"], paquete["informe"]
        else:
            salida, informe = procesar_datos(datos, fecha_referencia=referencia, configuracion=configuracion)
        # Mide preparación, sin lectura, escritura, exportación de fragmentos ni IA.
        tiempo_procesamiento_seg = round(time.perf_counter() - tiempo_procesamiento_inicio, 6)
        # Validar toda la entrega antes de escribir la primera salida.
        ciclos = None
        if argumentos.tamano_ciclo is not None:
            ciclos = construir_ciclos(paquete["completos"] if paquete else salida, argumentos.tamano_ciclo)
            validar_destino_ciclos(argumentos.ciclos, ciclos)
        guardar_json(argumentos.salida, salida)
        guardar_json(argumentos.informe, informe)
        if paquete:
            for ruta, clave in zip(adicionales, ("completos", "estados", "plan")):
                guardar_json(ruta, paquete[clave])
        ruta_manifest = None
        if ciclos is not None:
            ruta_manifest = guardar_ciclos(argumentos.ciclos, ciclos)
        if argumentos.registro_rendimiento is not None:
            guardar_json(argumentos.registro_rendimiento, {
                "version": "1.0",
                "alcance_tiempo": "preparacion_datos_sin_lectura_escritura_fragmentos_ni_ia",
                "tiempo_procesamiento_seg": tiempo_procesamiento_seg,
                "rendimiento": informe["rendimiento"],
            })
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps(informe["resumen"], ensure_ascii=False))
    rendimiento = informe["rendimiento"]
    print(json.dumps({
        "tiempo_procesamiento_seg": tiempo_procesamiento_seg,
        "tokens_estimados_total": rendimiento["tokens_estimados_total"],
        "tokens_estimados_analisis_total": rendimiento["tokens_estimados_analisis_total"],
        "tokens_estimados_contenido_total": rendimiento["tokens_estimados_contenido_total"],
        "caracteres_entrada_total": rendimiento["caracteres_entrada_total"],
        "caracteres_limpios_total": rendimiento["caracteres_limpios_total"],
        "caracteres_analisis_total": rendimiento["caracteres_analisis_total"],
        "caracteres_contenido_total": rendimiento["caracteres_contenido_total"],
        "lotes_con_alerta_caracteres": rendimiento["lotes_con_alerta_caracteres"],
    }, ensure_ascii=False))
    print(f"Datos: {argumentos.salida}\nInforme: {argumentos.informe}")
    if argumentos.registro_rendimiento is not None:
        print(f"Rendimiento: {argumentos.registro_rendimiento}")
    if ruta_manifest is not None:
        print(f"Ciclos: {ruta_manifest}")
    if paquete:
        print(json.dumps({"sentimiento": informe["resumen_sentimiento"],
                          "ciclos_procesamiento": [c["cantidad"] for c in paquete["plan"]["ciclos"]],
                          "pendientes": len(paquete["plan"]["pendientes"])}, ensure_ascii=False))
        for ruta in adicionales:
            print(ruta)


if __name__ == "__main__":
    principal()
