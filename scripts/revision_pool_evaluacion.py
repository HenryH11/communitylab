"""Revisión humana del pool v2: plantilla de 40 casos por fuente y resumen de acuerdo.

  python -m scripts.revision_pool_evaluacion plantilla --salida revision_pool_v2.csv
  python -m scripts.revision_pool_evaluacion resumen --revision revision_pool_v2.csv

La plantilla es un CSV en UTF-8 con BOM y separado por ";" (se abre bien en Excel
en español). El revisor deja vacía una columna "*_revisado" si está de acuerdo con
la etiqueta propuesta, o escribe la correcta. El resumen marca las reglas que fallan
en más del 10 % de la muestra (criterio de docs/pool_evaluacion_v2.md).
"""

import argparse
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

POOL = Path(__file__).resolve().parents[1] / "datos_evaluacion" / "pool_v2"
FUENTES = {"uca_ia_tweets.json": "sentimiento_esperado", "stackoverflow_es.json": "subtema_referencia"}
SEMILLA = 20261016
POR_FUENTE = 40
UMBRAL_ERROR = 0.10
DIMENSIONES = (("sentimiento", "sentimiento_esperado"), ("tema", "tema_esperado"), ("tipo", "tipo_esperado"))
COLUMNAS = ["id", "fuente", "texto",
            "sentimiento_propuesto", "tema_propuesto", "tipo_propuesto", "origen_etiquetas",
            "sentimiento_revisado", "tema_revisado", "tipo_revisado", "nota", "revisor"]


def muestra(casos, estrato, total, azar):
    grupos = defaultdict(list)
    for caso in sorted(casos, key=lambda c: c["id"]):
        grupos[caso[estrato]].append(caso)
    claves = sorted(grupos)
    elegidos = []
    for i, clave in enumerate(claves):
        cuota = total // len(claves) + (1 if i < total % len(claves) else 0)
        elegidos += azar.sample(grupos[clave], min(cuota, len(grupos[clave])))
    return sorted(elegidos, key=lambda c: c["id"])


def plantilla(salida, pool=POOL, por_fuente=POR_FUENTE, semilla=SEMILLA):
    azar = random.Random(semilla)
    filas = []
    for archivo, estrato in FUENTES.items():
        casos = json.loads((Path(pool) / archivo).read_text(encoding="utf-8"))["casos"]
        for caso in muestra(casos, estrato, por_fuente, azar):
            origen = caso.get("origen_etiquetas", {})
            filas.append({
                "id": caso["id"], "fuente": Path(archivo).stem, "texto": caso["texto"],
                "sentimiento_propuesto": caso["sentimiento_esperado"],
                "tema_propuesto": caso["tema_esperado"], "tipo_propuesto": caso["tipo_esperado"],
                "origen_etiquetas": ", ".join(f"{k}={v}" for k, v in sorted(origen.items())),
                "sentimiento_revisado": "", "tema_revisado": "", "tipo_revisado": "",
                "nota": "", "revisor": "",
            })
    with open(salida, "w", encoding="utf-8-sig", newline="") as destino:
        escritor = csv.DictWriter(destino, COLUMNAS, delimiter=";")
        escritor.writeheader()
        escritor.writerows(filas)
    return len(filas)


def resumen(ruta_revision):
    """Por fuente y dimensión: revisados, de acuerdo, tasa de error y si supera el umbral."""
    with open(ruta_revision, encoding="utf-8-sig", newline="") as origen:
        filas = list(csv.DictReader(origen, delimiter=";"))
    conteo = defaultdict(lambda: {"revisados": 0, "corregidos": 0})
    for fila in filas:
        if not fila.get("revisor", "").strip():
            continue
        for nombre, _ in DIMENSIONES:
            celda = conteo[(fila["fuente"], nombre)]
            celda["revisados"] += 1
            revisado = fila.get(f"{nombre}_revisado", "").strip()
            if revisado and revisado != fila[f"{nombre}_propuesto"]:
                celda["corregidos"] += 1
    salida = {}
    for (fuente, nombre), celda in sorted(conteo.items()):
        tasa = celda["corregidos"] / celda["revisados"] if celda["revisados"] else 0.0
        salida.setdefault(fuente, {})[nombre] = {
            **celda, "tasa_error": round(tasa, 3), "corregir_regla": tasa > UMBRAL_ERROR}
    return salida


def principal(argumentos=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p_plantilla = sub.add_parser("plantilla")
    p_plantilla.add_argument("--salida", required=True)
    p_plantilla.add_argument("--por-fuente", type=int, default=POR_FUENTE)
    p_resumen = sub.add_parser("resumen")
    p_resumen.add_argument("--revision", required=True)
    args = parser.parse_args(argumentos)
    if args.comando == "plantilla":
        print(json.dumps({"casos": plantilla(args.salida, por_fuente=args.por_fuente)}))
    else:
        print(json.dumps(resumen(args.revision), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
