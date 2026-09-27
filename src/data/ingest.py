"""Lectura, validación, limpieza y selección de JSON para el pipeline de IA."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import re
import unicodedata

if __package__:
    from .relevancia import ConfigRelevancia, leer_fecha, seleccionar_lote
else:
    from relevancia import ConfigRelevancia, leer_fecha, seleccionar_lote


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


def limpiar_texto(texto):
    texto = unicodedata.normalize("NFC", html.unescape(texto))
    texto = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", " ", texto, flags=re.I | re.S)
    texto = ETIQUETAS.sub(" ", texto)
    texto = "".join(
        " " if unicodedata.category(c) == "Cc" or c == "\ufffd" else c
        for c in texto if c not in {"\u200b", "\ufeff"}
    )
    return " ".join(texto.split())


def _cadena(objeto, campo, ruta, vacia=False):
    valor = objeto.get(campo)
    if not isinstance(valor, str) or (not vacia and not valor.strip()):
        raise ValueError(f"{ruta}.{campo}: se esperaba texto" + (" no vacío" if not vacia else ""))


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
            if mensaje["tipo"] not in {"testimonio", "pregunta_tecnica", "comentario", "feedback"}:
                raise ValueError(f"{ubicacion}.tipo: valor no admitido")
            for campo in ("id", "fecha", "idioma"):
                if campo in mensaje:
                    _cadena(mensaje, campo, ubicacion)
            for campo in ("autor", "canal", "texto"):
                mensaje[campo] = limpiar_texto(mensaje[campo])
            for campo in ("autor", "canal"):
                _cadena(mensaje, campo, ubicacion)
    return resultado


def procesar_datos(datos, *, fecha_referencia, config=None):
    """Devuelve (datos seleccionados, informe). No modifica datos ni usa red/reloj."""
    config = config if config is not None else ConfigRelevancia()
    if isinstance(fecha_referencia, str):
        fecha_referencia = leer_fecha(fecha_referencia)
    if not isinstance(fecha_referencia, datetime) or fecha_referencia.tzinfo is None:
        raise ValueError("fecha_referencia debe incluir zona horaria")
    salida = validar_y_limpiar(datos)
    lotes = salida["lotes"] if "lotes" in salida else [salida]
    informe = {
        "version_criterio": "1.0-propuesta",
        "fecha_referencia": fecha_referencia.astimezone(timezone.utc).isoformat(),
        "configuracion": config.como_dict(),
        "resumen": {"total": 0, "seleccionadas": 0, "descartadas": 0},
        "lotes": [],
    }
    for indice, lote in enumerate(lotes):
        seleccionadas, evaluaciones = seleccionar_lote(lote, config, fecha_referencia)
        lote["interacciones"] = seleccionadas
        informe["lotes"].append({
            "indice": indice, "origen_comunidad": lote["origen_comunidad"],
            "periodo_referencia": lote["periodo_referencia"], "evaluaciones": evaluaciones,
        })
        informe["resumen"]["total"] += len(evaluaciones)
        informe["resumen"]["seleccionadas"] += len(seleccionadas)
    informe["resumen"]["descartadas"] = informe["resumen"]["total"] - informe["resumen"]["seleccionadas"]
    return salida, informe


def construir_estado_agente(mensaje, puntaje, origen):
    """Traduce una interacción ya depurada al subconjunto de entrada de `AgentState`
    (ver `src/agents/state.py`, Sub-equipo 2), confirmado con Data Science:

    - `autor`, `canal`, `texto`: sin cambios.
    - `tipo` no se modifica ni se renombra; se copia (no se reemplaza) hacia
      `tipo_original`, que Data Science usa para comparar contra su propia
      clasificación posterior.
    - `puntaje` (de `relevancia.py`) se expone como `score_relevancia`.
    - `origen` viene de `origen_comunidad` del lote, bajado a nivel de interacción.
    - `id`/`idioma` se incluyen solo si la interacción los trae (son opcionales en
      el contrato); no se fabrica ningún valor por defecto.

    No incluye campos que produce Data Science (`sentimiento`, `rutas`,
    `activos_generados`, etc.) — esos se agregan más adelante en su propio grafo.
    """
    estado = {
        "autor": mensaje["autor"],
        "canal": mensaje["canal"],
        "origen": origen,
        "texto": mensaje["texto"],
        "tipo_original": mensaje["tipo"],
        "score_relevancia": puntaje,
    }
    for campo in ("id", "idioma"):
        if campo in mensaje:
            estado[campo] = mensaje[campo]
    return estado


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
            estados.append(construir_estado_agente(interaccion, evaluacion["puntaje"], lote["origen_comunidad"]))
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
    frontera. Falla si falta alguno — en el dataset real de hoy los siete están
    presentes en el 100% de los casos, así que cumplirlo no cuesta nada."""
    faltantes = [campo for campo in _CAMPOS_CONTRATO_NELSON if campo not in interaccion]
    if faltantes:
        raise ValueError(
            "Interacción sin los campos obligatorios del contrato de entrega "
            f"({', '.join(_CAMPOS_CONTRATO_NELSON)}): faltan {', '.join(faltantes)}"
        )
    for campo in _CAMPOS_CONTRATO_NELSON:
        _cadena(interaccion, campo, "interaccion", vacia=campo == "texto" and permitir_texto_vacio)
    if interaccion["tipo"] not in {"testimonio", "pregunta_tecnica", "comentario", "feedback"}:
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
    raiz_output = (RAIZ / "output").resolve()
    if raiz_output not in directorio_ciclos.parents:
        raise ValueError("directorio_ciclos debe ser una subcarpeta dentro de output/")
    if directorio_ciclos.exists() and not directorio_ciclos.is_dir():
        raise ValueError("El destino de ciclos no es un directorio")
    def ruta_archivo(nombre):
        if not isinstance(nombre, str) or not re.fullmatch(r"[A-Za-z0-9_-]+_lote\d+_ciclo\d+\.json", nombre):
            raise ValueError("Nombre de fragmento inválido")
        ruta = directorio_ciclos / nombre
        if ruta.is_symlink() or ruta.resolve().parent != directorio_ciclos or (ruta.exists() and not ruta.is_file()):
            raise ValueError("Ruta de fragmento no segura")
        return ruta
    manifest = directorio_ciclos / "manifest.json"
    if manifest.is_symlink() or (manifest.exists() and not manifest.is_file()):
        raise ValueError("Ruta de manifest no segura")
    anteriores = set()
    if manifest.exists():
        previo = cargar_json(manifest)
        if not isinstance(previo, dict) or not isinstance(previo.get("ciclos"), list):
            raise ValueError("Manifest anterior inválido; no se modifica la carpeta")
        for entrada in previo["ciclos"]:
            if not isinstance(entrada, dict) or "archivo" not in entrada:
                raise ValueError("Manifest anterior inválido")
            anteriores.add(ruta_archivo(entrada["archivo"]))
    nuevos = [ruta_archivo(c["archivo"]) for c in ciclos]
    if len(set(nuevos)) != len(nuevos):
        raise ValueError("Nombres de fragmentos repetidos")
    if any(p.exists() and p not in anteriores for p in nuevos):
        raise ValueError("Un fragmento sobrescribiría un archivo ajeno al manifest")
    return directorio_ciclos, anteriores, set(nuevos)


def guardar_ciclos(directorio_ciclos, ciclos):
    """Actualiza fragmentos; solo retira archivos enumerados en el manifest previo."""
    directorio_ciclos, anteriores, nuevos = validar_destino_ciclos(directorio_ciclos, ciclos)
    directorio_ciclos.mkdir(parents=True, exist_ok=True)
    for ciclo in ciclos:
        guardar_json(directorio_ciclos / ciclo["archivo"], ciclo["contenido"])
    ruta_manifest = directorio_ciclos / "manifest.json"
    guardar_json(ruta_manifest, {"ciclos": [
        {"archivo": c["archivo"], "lote_indice": c["lote_indice"], "ciclo_indice": c["ciclo_indice"], "cantidad": c["cantidad"]}
        for c in ciclos
    ]})
    for anterior in anteriores - nuevos:
        anterior.unlink(missing_ok=True)
    return ruta_manifest


def cargar_json(ruta):
    with Path(ruta).open(encoding="utf-8-sig") as archivo:
        return json.load(archivo)


def guardar_json(ruta, datos):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=RAIZ / "src/data/mensajes_comunidad_simulados.json")
    parser.add_argument("--salida", type=Path, default=RAIZ / "output/datos/mensajes_filtrados.json")
    parser.add_argument("--informe", type=Path, default=RAIZ / "output/datos/informe_relevancia.json")
    parser.add_argument("--config", type=Path, help="JSON con parámetros de ConfigRelevancia")
    parser.add_argument("--fecha-referencia", help="ISO 8601 con zona; por defecto, instante actual UTC")
    parser.add_argument("--top-n", type=int, help="Máximo de mensajes por lote tras aplicar el umbral")
    parser.add_argument("--min-puntaje", type=int, help="Umbral de selección de 0 a 100")
    parser.add_argument("--tamano-ciclo", type=int, help="Máximo N entre 10 y 30 para fragmentos y plan de entrega; activa archivos por origen")
    parser.add_argument("--ciclos", type=Path, default=RAIZ / "output/datos/entregas", help="Directorio de los archivos-ciclo; solo se usa junto con --tamano-ciclo")
    parser.add_argument("--entrega-ia", type=Path, metavar="DIR", help="Exporta población completa, AgentState y plan de ciclos en DIR, sin llamar a IA")
    args = parser.parse_args(argv)
    try:
        salidas = [args.salida.resolve(), args.informe.resolve()]
        adicionales = []
        if args.entrega_ia is not None:
            adicionales = [args.entrega_ia / nombre for nombre in (
                "mensajes_limpios_completos.json", "estados_agente.json", "plan_procesamiento.json",
            )]
            salidas.extend(p.resolve() for p in adicionales)
        entradas = [args.entrada.resolve()] + ([args.config.resolve()] if args.config else [])
        if len(set(salidas)) != len(salidas) or any(p in entradas for p in salidas):
            raise ValueError("Entrada, configuración, salida e informe deben usar archivos distintos")
        if any(p.exists() and not p.is_file() for p in salidas):
            raise ValueError("Una salida coincide con un directorio")
        if any(p in q.parents for p in salidas + entradas for q in salidas):
            raise ValueError("Un archivo no puede usarse como directorio de salida")
        if args.tamano_ciclo is not None:
            validar_tamano_ciclo(args.tamano_ciclo)
            ciclos_resuelto = args.ciclos.resolve()
            if any(p == ciclos_resuelto or ciclos_resuelto in p.parents for p in entradas + salidas):
                raise ValueError("--ciclos no puede coincidir con la entrada, configuración, salida o informe")
        opciones = cargar_json(args.config) if args.config else {}
        if not isinstance(opciones, dict):
            raise ValueError("La configuración debe ser un objeto JSON")
        for campo in ("top_n", "min_puntaje"):
            if getattr(args, campo) is not None:
                opciones[campo] = getattr(args, campo)
        config = ConfigRelevancia(**opciones)
        referencia = args.fecha_referencia or datetime.now(timezone.utc).isoformat()
        datos = cargar_json(args.entrada)
        paquete = None
        if args.entrega_ia is not None:
            if not __package__:
                import sys
                sys.path.insert(0, str(RAIZ))
            from src.data.entrega_ia import preparar_paquete_ia
            paquete = preparar_paquete_ia(datos, fecha_referencia=referencia, config=config,
                                          tamano_ciclo=args.tamano_ciclo if args.tamano_ciclo is not None else 20)
            salida, informe = paquete["contenido"], paquete["informe"]
        else:
            salida, informe = procesar_datos(datos, fecha_referencia=referencia, config=config)
        # Validar toda la entrega antes de escribir la primera salida.
        ciclos = None
        if args.tamano_ciclo is not None:
            ciclos = construir_ciclos(paquete["completos"] if paquete else salida, args.tamano_ciclo)
            validar_destino_ciclos(args.ciclos, ciclos)
        guardar_json(args.salida, salida)
        guardar_json(args.informe, informe)
        if paquete:
            for ruta, clave in zip(adicionales, ("completos", "estados", "plan")):
                guardar_json(ruta, paquete[clave])
        ruta_manifest = None
        if ciclos is not None:
            ruta_manifest = guardar_ciclos(args.ciclos, ciclos)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps(informe["resumen"], ensure_ascii=False))
    print(f"Datos: {args.salida}\nInforme: {args.informe}")
    if ruta_manifest is not None:
        print(f"Ciclos: {ruta_manifest}")
    if paquete:
        print(json.dumps({"sentimiento": informe["resumen_sentimiento"],
                          "ciclos_procesamiento": [c["cantidad"] for c in paquete["plan"]["ciclos"]],
                          "pendientes": len(paquete["plan"]["pendientes"])}, ensure_ascii=False))
        for ruta in adicionales:
            print(ruta)


if __name__ == "__main__":
    main()
