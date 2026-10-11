"""Lectura, validación, limpieza y selección de JSON para el flujo de IA."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import time
from typing import TYPE_CHECKING, cast
import unicodedata

if TYPE_CHECKING:
    from src.agentes.estado_agente import EstadoAgente

if __package__:
    from .relevancia import TIPOS, ConfiguracionRelevancia, leer_fecha, seleccionar_lote
else:
    from relevancia import TIPOS, ConfiguracionRelevancia, leer_fecha, seleccionar_lote


RAIZ = Path(__file__).resolve().parents[2]
# Lista acotada: conserva expresiones técnicas como a < b y tipos como <T>.
ETIQUETAS = re.compile(
    r"</?(?:p|div|span|br|a|b|strong|em|i|ul|ol|li|pre|code|blockquote|h[1-6])\b[^>]*>",
    re.IGNORECASE,
)
_CARACTERES_NO_SEGUROS_ARCHIVO = re.compile(r"[^A-Za-z0-9_-]+")


def _nombre_seguro(texto):
    """Reduce un campo de datos (origen_comunidad, periodo_referencia) a algo
    seguro para usar en un nombre de archivo: solo letras/números/guiones. Evita
    que un valor con `/` o `..` escriba fuera del directorio de ciclos."""
    limpio = _CARACTERES_NO_SEGUROS_ARCHIVO.sub("_", texto).strip("_")
    return limpio or "sin_nombre"


def _texto_visible(texto):
    """Decodifica HTML y elimina solo el marcado que la limpieza admite."""
    texto = unicodedata.normalize("NFC", html.unescape(texto))
    texto = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", " ", texto, flags=re.I | re.S)
    return ETIQUETAS.sub(" ", texto)


def limpiar_texto(texto):
    texto = _texto_visible(texto)
    texto = "".join(
        " " if unicodedata.category(c) == "Cc" or c == "\ufffd" else c
        for c in texto if c not in {"\u200b", "\ufeff"}
    )
    return " ".join(texto.split())


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


def estimar_tokens(texto):
    """Aproxima el consumo de tokens de un texto (~4 caracteres por token).

    Solo estima el texto. No incluye prompts, metadatos, respuestas ni
    reintentos, por lo que no representa cuota ni facturación de Gemini.
    """
    return max(1, round(len(texto) / 4)) if texto else 0


_CATEGORIAS_CONTROL = {"Cc", "Cf"}


def contar_caracteres_no_ascii(texto):
    """Cuenta caracteres no ASCII 'significativos' (tildes, ñ, emojis, etc.),

    excluyendo control/formato invisibles. Es un conteo auxiliar, no una
    garantía de conservación del texto.
    """
    return sum(
        1 for c in texto
        if ord(c) > 127 and unicodedata.category(c) not in _CATEGORIAS_CONTROL
    )


def caracteres_especiales_preservados(original, limpio):
    """Compara identidad y orden de Unicode visible, normalizado a NFC.

    Admite la retirada de HTML, scripts, controles y espacios. Conserva los
    unidores de emojis. U+FFFD avisa de una pérdida previa de información.
    No detecta todos los casos posibles de texto previamente mal decodificado.
    """
    visible = _texto_visible(original)
    if "\ufffd" in visible or "\ufffd" in limpio:
        return False

    def secuencia(texto):
        return [c for c in unicodedata.normalize("NFC", texto)
                if ord(c) > 127 and not c.isspace()
                and unicodedata.category(c) != "Cc"
                and c not in {"\u200b", "\ufeff"}]

    return secuencia(visible) == secuencia(limpio)


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


_CAMPOS_CONTRATO_NELSON = ("id", "autor", "canal", "tipo", "texto", "fecha", "idioma")


def _interaccion_para_entrega(interaccion, *, permitir_texto_vacio=False):
    """Proyecta una interacción ya depurada al contrato oficial de Nelson
    (`docs/arquitectura-solucion/contrato-intermedio-ingesta.schema.json`):
    exactamente `id`/`autor`/`canal`/`tipo`/`texto`/`fecha`/`idioma`, los siete
    obligatorios y sin campos adicionales (`additionalProperties: false`). Los
    campos internos nuestros (o cualquier extensión ajena) no cruzan esta
    frontera. Falla si falta alguno — en el conjunto_datos real de hoy los siete están
    presentes en el 100% de los casos, así que cumplirlo no cuesta nada."""
    faltantes = [campo for campo in _CAMPOS_CONTRATO_NELSON if campo not in interaccion]
    if faltantes:
        raise ValueError(
            "Interacción sin los campos obligatorios del contrato de entrega "
            f"({', '.join(_CAMPOS_CONTRATO_NELSON)}): faltan {', '.join(faltantes)}"
        )
    for campo in _CAMPOS_CONTRATO_NELSON:
        _cadena(interaccion, campo, "interaccion", vacia=campo == "texto" and permitir_texto_vacio)
    if interaccion["tipo"] not in TIPOS:
        raise ValueError("Tipo no admitido en la entrega")
    if interaccion["id"] != interaccion["id"].strip():
        raise ValueError("ID con espacios exteriores")
    fecha = interaccion["fecha"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", fecha):
        raise ValueError("fecha debe ser ISO 8601 completa con zona horaria")
    try:
        leer_fecha(fecha)
    except ValueError as error:
        raise ValueError("fecha inválida en la entrega") from error
    return {campo: interaccion[campo] for campo in _CAMPOS_CONTRATO_NELSON}


def validar_tamano_ciclo(tamano):
    if type(tamano) is not int or not 10 <= tamano <= 30:
        raise ValueError("tamano_ciclo debe ser un entero entre 10 y 30")


def construir_ciclos(salida, tamano_ciclo):
    """Exporta fragmentos planos por origen, conservando el orden recibido.

    N debe estar entre 10 y 30; un fragmento final puede tener menos de 10.
    Estos archivos son transporte, no los ciclos operativos: esos se definen
    en construir_plan_procesamiento. Cada interacción tiene siete campos válidos
    e ID único en la entrega. Un lote vacío no genera archivos.
    """
    validar_tamano_ciclo(tamano_ciclo)
    datos = validar_y_limpiar(salida)
    lotes = datos["lotes"] if "lotes" in datos else [datos]
    ciclos = []
    vistos = set()
    for lote_indice, lote in enumerate(lotes):
        interacciones = lote["interacciones"]
        origen = _nombre_seguro(lote["origen_comunidad"])
        periodo = _nombre_seguro(lote["periodo_referencia"])
        for ciclo_indice, inicio in enumerate(range(0, len(interacciones), tamano_ciclo)):
            fragmento = [_interaccion_para_entrega(i) for i in interacciones[inicio:inicio + tamano_ciclo]]
            for mensaje in fragmento:
                if mensaje["id"] in vistos:
                    raise ValueError("IDs repetidos en la entrega")
                vistos.add(mensaje["id"])
            ciclos.append({
                "archivo": f"{origen}_{periodo}_lote{lote_indice}_ciclo{ciclo_indice}.json",
                "contenido": {
                    "origen_comunidad": lote["origen_comunidad"],
                    "periodo_referencia": lote["periodo_referencia"],
                    "interacciones": fragmento,
                },
                "lote_indice": lote_indice,
                "ciclo_indice": ciclo_indice,
                "cantidad": len(fragmento),
            })
    return ciclos


def validar_destino_ciclos(directorio_ciclos, ciclos):
    """Comprueba rutas y propiedad de archivos antes de escribir o retirar nada."""
    directorio_ciclos = Path(directorio_ciclos).resolve()
    raiz_salida = (RAIZ / "salida").resolve()
    if raiz_salida not in directorio_ciclos.parents:
        raise ValueError("directorio_ciclos debe estar dentro de salida/")
    if directorio_ciclos.exists() and not directorio_ciclos.is_dir():
        raise ValueError("El destino de ciclos no es un directorio")
    def ruta_archivo(nombre):
        if not isinstance(nombre, str) or not re.fullmatch(r"[A-Za-z0-9_-]+_lote\d+_ciclo\d+\.json", nombre):
            raise ValueError("Nombre de fragmento inválido")
        ruta = directorio_ciclos / nombre
        if ruta.is_symlink() or ruta.resolve().parent != directorio_ciclos or (ruta.exists() and not ruta.is_file()):
            raise ValueError("Ruta de fragmento no segura")
        return ruta
    ruta_manifiesto = directorio_ciclos / "manifiesto.json"
    if ruta_manifiesto.is_symlink() or (ruta_manifiesto.exists() and not ruta_manifiesto.is_file()):
        raise ValueError("La ruta del manifiesto no es segura")
    anteriores = set()
    if ruta_manifiesto.exists():
        previo = cargar_json(ruta_manifiesto)
        if not isinstance(previo, dict) or not isinstance(previo.get("ciclos"), list):
            raise ValueError("El manifiesto anterior no es válido; no se modifica la carpeta")
        for entrada in previo["ciclos"]:
            if not isinstance(entrada, dict) or "archivo" not in entrada:
                raise ValueError("El manifiesto anterior no es válido")
            anteriores.add(ruta_archivo(entrada["archivo"]))
    nuevos = [ruta_archivo(c["archivo"]) for c in ciclos]
    if len(set(nuevos)) != len(nuevos):
        raise ValueError("Nombres de fragmentos repetidos")
    if any(p.exists() and p not in anteriores for p in nuevos):
        raise ValueError("Un fragmento sobrescribiría un archivo ajeno al manifiesto")
    return directorio_ciclos, anteriores, set(nuevos)


def guardar_ciclos(directorio_ciclos, ciclos):
    """Actualiza fragmentos y solo retira archivos del manifiesto anterior."""
    directorio_ciclos, anteriores, nuevos = validar_destino_ciclos(directorio_ciclos, ciclos)
    directorio_ciclos.mkdir(parents=True, exist_ok=True)
    for ciclo in ciclos:
        guardar_json(directorio_ciclos / ciclo["archivo"], ciclo["contenido"])
    ruta_manifiesto = directorio_ciclos / "manifiesto.json"
    guardar_json(ruta_manifiesto, {"ciclos": [
        {"archivo": c["archivo"], "lote_indice": c["lote_indice"], "ciclo_indice": c["ciclo_indice"], "cantidad": c["cantidad"]}
        for c in ciclos
    ]})
    for anterior in anteriores - nuevos:
        anterior.unlink(missing_ok=True)
    return ruta_manifiesto


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
