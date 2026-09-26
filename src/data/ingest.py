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


def construir_estados_agente(salida, informe):
    """Aplana los lotes ya seleccionados de `procesar_datos` en una lista de dicts
    `AgentState` (uno por interacción seleccionada), en el mismo orden de
    relevancia con el que `seleccionar_lote` ya los entrega."""
    estados = []
    lotes_salida = salida["lotes"] if "lotes" in salida else [salida]
    for lote, reporte_lote in zip(lotes_salida, informe["lotes"]):
        seleccionadas = sorted(
            (e for e in reporte_lote["evaluaciones"] if e["seleccionado"]),
            key=lambda e: (-e["puntaje"], e["indice"]),
        )
        for interaccion, evaluacion in zip(lote["interacciones"], seleccionadas):
            estados.append(construir_estado_agente(interaccion, evaluacion["puntaje"], lote["origen_comunidad"]))
    return estados


_CAMPOS_CONTRATO_NELSON = ("id", "autor", "canal", "tipo", "texto", "fecha", "idioma")


def _interaccion_para_entrega(interaccion):
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
    return {campo: interaccion[campo] for campo in _CAMPOS_CONTRATO_NELSON}


def construir_ciclos(salida, tamano_ciclo):
    """Parte, por lote, la lista ya seleccionada de interacciones (viene ordenada
    por relevancia descendente) en archivos-ciclo consecutivos de a lo sumo
    `tamano_ciclo` interacciones cada uno. Cada ciclo conserva exactamente la
    forma plana `{origen_comunidad, periodo_referencia, interacciones}` y cada
    interacción se proyecta al contrato oficial de Nelson vía
    `_interaccion_para_entrega` — sin envoltorio, sin campos adicionales, y con
    los siete campos obligatorios. Reparte primero lo más relevante. Un lote
    vacío no genera ningún ciclo. Función pura: no toca disco ni depende de nada
    externo."""
    if not isinstance(tamano_ciclo, int) or isinstance(tamano_ciclo, bool) or tamano_ciclo < 1:
        raise ValueError("tamano_ciclo debe ser un entero positivo")
    lotes = salida["lotes"] if "lotes" in salida else [salida]
    ciclos = []
    for lote_indice, lote in enumerate(lotes):
        interacciones = lote["interacciones"]
        origen = _nombre_seguro(lote["origen_comunidad"])
        periodo = _nombre_seguro(lote["periodo_referencia"])
        for ciclo_indice, inicio in enumerate(range(0, len(interacciones), tamano_ciclo)):
            fragmento = [_interaccion_para_entrega(i) for i in interacciones[inicio:inicio + tamano_ciclo]]
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


def guardar_ciclos(directorio_ciclos, ciclos):
    """Limpia `directorio_ciclos` (validando que quede dentro de `output/`, nunca
    fuera) y escribe cada archivo-ciclo más un `manifest.json` que los enumera.
    Todo el contenido ya fue construido en memoria por `construir_ciclos` antes
    de escribir el primer archivo. El nombre de archivo es solo para navegación
    humana; `manifest.json` es el único punto de verificación a parsear."""
    directorio_ciclos = Path(directorio_ciclos).resolve()
    raiz_output = (RAIZ / "output").resolve()
    if directorio_ciclos != raiz_output and raiz_output not in directorio_ciclos.parents:
        raise ValueError("directorio_ciclos debe estar dentro de output/")
    if directorio_ciclos.is_dir():
        for existente in directorio_ciclos.iterdir():
            if existente.is_file():
                existente.unlink()
    directorio_ciclos.mkdir(parents=True, exist_ok=True)
    for ciclo in ciclos:
        guardar_json(directorio_ciclos / ciclo["archivo"], ciclo["contenido"])
    ruta_manifest = directorio_ciclos / "manifest.json"
    guardar_json(ruta_manifest, {"ciclos": [
        {"archivo": c["archivo"], "lote_indice": c["lote_indice"], "ciclo_indice": c["ciclo_indice"], "cantidad": c["cantidad"]}
        for c in ciclos
    ]})
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
    parser.add_argument("--tamano-ciclo", type=int, help="Activa la entrega en archivos-ciclo de a lo sumo N interacciones (opt-in; sin este flag, la salida no cambia)")
    parser.add_argument("--ciclos", type=Path, default=RAIZ / "output/datos/entregas", help="Directorio de los archivos-ciclo; solo se usa junto con --tamano-ciclo")
    args = parser.parse_args(argv)
    try:
        salidas = [args.salida.resolve(), args.informe.resolve()]
        entradas = [args.entrada.resolve()] + ([args.config.resolve()] if args.config else [])
        if len(set(salidas)) != 2 or any(p in entradas for p in salidas):
            raise ValueError("Entrada, configuración, salida e informe deben usar archivos distintos")
        if args.tamano_ciclo is not None:
            ciclos_resuelto = args.ciclos.resolve()
            if ciclos_resuelto in salidas or any(p == ciclos_resuelto or p.parent == ciclos_resuelto for p in entradas):
                raise ValueError("--ciclos no puede coincidir con la entrada, configuración, salida o informe")
        opciones = cargar_json(args.config) if args.config else {}
        if not isinstance(opciones, dict):
            raise ValueError("La configuración debe ser un objeto JSON")
        for campo in ("top_n", "min_puntaje"):
            if getattr(args, campo) is not None:
                opciones[campo] = getattr(args, campo)
        config = ConfigRelevancia(**opciones)
        referencia = args.fecha_referencia or datetime.now(timezone.utc).isoformat()
        salida, informe = procesar_datos(cargar_json(args.entrada), fecha_referencia=referencia, config=config)
        guardar_json(args.salida, salida)
        guardar_json(args.informe, informe)
        ruta_manifest = None
        if args.tamano_ciclo is not None:
            ciclos = construir_ciclos(salida, args.tamano_ciclo)
            ruta_manifest = guardar_ciclos(args.ciclos, ciclos)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps(informe["resumen"], ensure_ascii=False))
    print(f"Datos: {args.salida}\nInforme: {args.informe}")
    if ruta_manifest is not None:
        print(f"Ciclos: {ruta_manifest}")


if __name__ == "__main__":
    main()
