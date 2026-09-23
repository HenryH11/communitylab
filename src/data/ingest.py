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
    args = parser.parse_args(argv)
    try:
        salidas = [args.salida.resolve(), args.informe.resolve()]
        entradas = [args.entrada.resolve()] + ([args.config.resolve()] if args.config else [])
        if len(set(salidas)) != 2 or any(p in entradas for p in salidas):
            raise ValueError("Entrada, configuración, salida e informe deben usar archivos distintos")
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
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Error: {error}\n")
    print(json.dumps(informe["resumen"], ensure_ascii=False))
    print(f"Datos: {args.salida}\nInforme: {args.informe}")


if __name__ == "__main__":
    main()
