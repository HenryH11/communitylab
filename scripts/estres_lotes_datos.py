"""Auditoría de estrés de la línea de Datos (Semana 4, tarea ALL de la Matriz 2).

Corre al mismo tiempo los 3 lotes simulados (casos de éxito, dudas de FAQ y
ruido/spam), por separado y juntos, por la preparación de Datos: validación, limpieza, relevancia,
población de sentimiento, estados del agente y plan de ciclos. Certifica que no
haya caídas, que cada corrida concurrente dé el mismo resultado que la corrida
de referencia y que la entrada no se modifique. También prueba volumen (cada lote
ampliado N veces) y texto con mojibake, que debe repararse al original.

No llama a modelos de IA, a OCI ni a la red: cubre la parte de Datos de la línea.
La corrida con IA la hace DS con su propio paquete.

    python scripts/estres_lotes_datos.py --fecha-referencia 2026-09-17T12:00:00Z
    python scripts/estres_lotes_datos.py --repeticiones 50 --hilos 8 --volumen 200 --salida-json reporte.json
"""

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.datos.entrega_ia import preparar_paquete_ia  # noqa: E402
from src.datos.relevancia import ConfiguracionRelevancia  # noqa: E402

FIXTURE = RAIZ / "tests/fixtures/lotes_estres_semana4.json"
CONFIGURACION = RAIZ / "configuracion/relevancia.json"
FECHA_REFERENCIA = "2026-09-17T12:00:00Z"


def separar_lotes(datos):
    """Un contenedor por lote, para correrlos como entregas independientes y en paralelo."""
    return [{"lotes": [lote]} for lote in datos["lotes"]]


def ampliar(entrega, factor):
    """Repite el lote `factor` veces con IDs y autores distintos, para que no cuenten como copias."""
    lote = entrega["lotes"][0]
    interacciones = [
        dict(m, id=f"{m['id']}-v{numero:04d}", autor=f"{m['autor']} {numero}")
        for numero in range(factor) for m in lote["interacciones"]
    ]
    return {"lotes": [dict(lote, interacciones=interacciones)]}


def leer_como_cp1252(texto):
    """Como lo lee Windows: los 5 bytes sin carácter en CP1252 (0x81, 0x8D, 0x8F, 0x90, 0x9D) quedan como controles C1."""
    return "".join(
        bytes([b]).decode("cp1252", errors="ignore") or chr(b) for b in texto.encode("utf-8")
    )


def con_mojibake(entrega):
    """El mismo lote como si sus textos UTF-8 se hubieran leído en Windows-1252."""
    lote = deepcopy(entrega["lotes"][0])
    for mensaje in lote["interacciones"]:
        mensaje["texto"] = leer_como_cp1252(mensaje["texto"])
    return {"lotes": [lote]}


def resumir(paquete):
    """Lo que se compara entre corridas y se reporta por lote."""
    informe = paquete["informe"]
    evaluaciones = [e for lote in informe["lotes"] for e in lote["evaluaciones"]]
    return {
        "total": informe["resumen"]["total"],
        "seleccionadas_contenido": informe["resumen"]["seleccionadas"],
        "incluidas_sentimiento": informe["resumen_sentimiento"]["incluidas"],
        "excluidas_calidad": informe["resumen_sentimiento"]["excluidas_calidad"],
        "motivos": dict(sorted(Counter(m for e in evaluaciones for m in e["motivos"]).items())),
        "elegibles_faq": sum(e["elegible_faq"] for e in evaluaciones),
        "ciclos": [c["cantidad"] for c in paquete["plan"]["ciclos"]],
        "pendientes": len(paquete["plan"]["pendientes"]),
    }


CAMPOS_RESUMEN = ("total", "seleccionadas_contenido", "incluidas_sentimiento", "excluidas_calidad", "motivos",
                  "elegibles_faq", "ciclos", "pendientes")


def huella(paquete):
    return json.dumps(paquete, ensure_ascii=False, sort_keys=True)


def correr(entregas, *, fecha_referencia, configuracion, repeticiones, hilos):
    """Corre cada entrega `repeticiones` veces en paralelo y compara contra una corrida de referencia."""
    copias = [deepcopy(e) for e in entregas]

    def preparar(indice):
        try:
            return preparar_paquete_ia(entregas[indice], fecha_referencia=fecha_referencia,
                                       configuracion=configuracion), None
        except Exception as error:  # se cuenta como caída y se reporta, no se oculta
            return None, f"{type(error).__name__}: {error}"

    # Si la corrida de referencia también falla, se reporta como caída en vez de cortar la auditoría.
    referencia, errores_referencia = zip(*(preparar(i) for i in range(len(entregas))))
    referencia = list(referencia)
    esperadas = [huella(p) if p is not None else None for p in referencia]
    trabajos = [indice for _ in range(repeticiones) for indice in range(len(entregas))]

    def una(indice):
        inicio = time.perf_counter()
        paquete, error = preparar(indice)
        if error:
            return indice, error, False, time.perf_counter() - inicio
        return indice, None, huella(paquete) == esperadas[indice], time.perf_counter() - inicio

    with ThreadPoolExecutor(max_workers=hilos) as ejecutor:
        resultados = list(ejecutor.map(una, trabajos))
    lotes = []
    for indice, entrega in enumerate(entregas):
        propios = [r for r in resultados if r[0] == indice]
        tiempos = sorted(r[3] for r in propios)
        error_referencia = errores_referencia[indice]
        paquete_referencia = referencia[indice]
        resumen: dict[str, Any] = (
            resumir(paquete_referencia) if paquete_referencia is not None else dict.fromkeys(CAMPOS_RESUMEN)
        )
        lotes.append({
            "origen_comunidad": " + ".join(lote["origen_comunidad"] for lote in entrega["lotes"]),
            "corridas": len(propios),
            "caidas": sum(r[1] is not None for r in propios) + bool(error_referencia),
            "errores": sorted({r[1] for r in propios if r[1]} | ({error_referencia} if error_referencia else set())),
            "distintas_a_la_referencia": sum(r[1] is None and not r[2] for r in propios),
            "entrada_intacta": entrega == copias[indice],
            "segundos_mediana": round(tiempos[len(tiempos) // 2], 6) if tiempos else None,
            "segundos_max": round(tiempos[-1], 6) if tiempos else None,
            **resumen,
        })
    return lotes, referencia


def auditar(datos, *, fecha_referencia=FECHA_REFERENCIA, configuracion=None, repeticiones=20, hilos=3, volumen=50):
    configuracion = configuracion or ConfiguracionRelevancia()
    entregas = separar_lotes(datos)
    # Los 3 lotes por separado y, además, juntos en una sola entrega (como llegaría un lote mixto).
    base, referencia = correr(entregas + [deepcopy(datos)], fecha_referencia=fecha_referencia,
                              configuracion=configuracion, repeticiones=repeticiones, hilos=hilos)
    ampliadas, _ = correr([ampliar(e, volumen) for e in entregas], fecha_referencia=fecha_referencia,
                          configuracion=configuracion, repeticiones=1, hilos=hilos)
    rotas = [con_mojibake(e) for e in entregas]
    reparadas, paquetes_rotos = correr(rotas, fecha_referencia=fecha_referencia, configuracion=configuracion,
                                       repeticiones=1, hilos=hilos)
    def textos_de(paquetes):
        return [[m["texto"] for m in p["completos"]["lotes"][0]["interacciones"]] if p is not None else None
                for p in paquetes]

    textos_originales = textos_de(referencia[:len(rotas)])
    textos_reparados = textos_de(paquetes_rotos)
    fases = {"base": base, "volumen": ampliadas, "mojibake": reparadas}
    caidas = sum(l["caidas"] for fase in fases.values() for l in fase)
    distintas = sum(l["distintas_a_la_referencia"] for fase in fases.values() for l in fase)
    modificadas = sum(not l["entrada_intacta"] for fase in fases.values() for l in fase)
    mojibake_reparado = None not in textos_originales and textos_originales == textos_reparados
    return {
        "version": "1.0",
        "fecha_referencia": fecha_referencia,
        "parametros": {"repeticiones": repeticiones, "hilos": hilos, "volumen": volumen},
        "alcance": "Preparación de Datos (validación, limpieza, relevancia, sentimiento, estados y plan). Sin IA, OCI ni red.",
        "fases": fases,
        "resumen": {
            "corridas": sum(l["corridas"] for fase in fases.values() for l in fase),
            "caidas": caidas,
            "distintas_a_la_referencia": distintas,
            "entradas_modificadas": modificadas,
            "mojibake_reparado": mojibake_reparado,
            "en_verde": not (caidas or distintas or modificadas) and mojibake_reparado,
        },
    }


def a_markdown(reporte):
    filas = []
    for nombre, fase in reporte["fases"].items():
        for l in fase:
            filas.append(
                f"| {nombre} | {l['origen_comunidad']} | {l['total']} | {l['incluidas_sentimiento']} | "
                f"{l['seleccionadas_contenido']} | {l['elegibles_faq']} | {l['corridas']} | {l['caidas']} | "
                f"{l['distintas_a_la_referencia']} | {l['segundos_max']} |"
            )
    r = reporte["resumen"]
    return "\n".join([
        f"Estado: {'EN VERDE' if r['en_verde'] else 'CON FALLAS'} · {r['corridas']} corridas · {r['caidas']} caídas · "
        f"{r['distintas_a_la_referencia']} distintas a la referencia · mojibake reparado: {'sí' if r['mojibake_reparado'] else 'no'}",
        "",
        "| Fase | Lote | Mensajes | Sentimiento | Contenido | FAQ | Corridas | Caídas | Distintas | Máx. (s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
        *filas,
    ]) + "\n"


def principal(argv=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    parser.add_argument("--entrada", type=Path, default=FIXTURE)
    parser.add_argument("--fecha-referencia", default=FECHA_REFERENCIA)
    parser.add_argument("--configuracion", type=Path, default=CONFIGURACION, help="JSON con parámetros de relevancia")
    parser.add_argument("--repeticiones", type=int, default=20)
    parser.add_argument("--hilos", type=int, default=3)
    parser.add_argument("--volumen", type=int, default=50, help="Veces que se repite cada lote en la fase de volumen")
    parser.add_argument("--salida-json", type=Path)
    parser.add_argument("--salida-md", type=Path)
    argumentos = parser.parse_args(argv)
    if min(argumentos.repeticiones, argumentos.hilos, argumentos.volumen) < 1:
        parser.error("--repeticiones, --hilos y --volumen deben ser enteros positivos")
    datos = json.loads(argumentos.entrada.read_text(encoding="utf-8"))
    opciones = json.loads(argumentos.configuracion.read_text(encoding="utf-8")) if argumentos.configuracion else {}
    reporte = auditar(datos, fecha_referencia=argumentos.fecha_referencia,
                      configuracion=ConfiguracionRelevancia(**opciones), repeticiones=argumentos.repeticiones,
                      hilos=argumentos.hilos, volumen=argumentos.volumen)
    if argumentos.salida_json:
        argumentos.salida_json.write_bytes((json.dumps(reporte, ensure_ascii=False, indent=4) + "\n").encode("utf-8"))
    if argumentos.salida_md:
        argumentos.salida_md.write_bytes(a_markdown(reporte).encode("utf-8"))
    print(a_markdown(reporte), end="")
    return 0 if reporte["resumen"]["en_verde"] else 1


if __name__ == "__main__":
    sys.exit(principal())
