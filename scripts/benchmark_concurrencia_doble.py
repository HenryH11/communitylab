import argparse
import hashlib
import json
import os
import time
from collections import Counter
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument(
    "--modo",
    choices=("base", "analisis", "generacion", "ambas"),
    required=True,
)
parser.add_argument("--corrida", type=int, default=1)
parser.add_argument("--tamano-lote", type=int, default=10)
parser.add_argument("--timeout-segundos", type=int, default=30)
parser.add_argument("--solo-validar", action="store_true")
parser.add_argument(
    "--modelo",
    choices=(
        "nvidia/nemotron-3-super-120b-a12b",
        "nvidia/nemotron-3.5-super-vl-120b-a12b",
    ),
    default="nvidia/nemotron-3-super-120b-a12b",
)
args = parser.parse_args()

if args.corrida < 1:
    parser.error("--corrida debe ser mayor que cero")
if not 1 <= args.tamano_lote <= 10:
    parser.error("--tamano-lote debe estar entre 1 y 10")

if args.timeout_segundos <= 0:
    parser.error("--timeout-segundos debe ser mayor que cero")

raiz = Path(__file__).resolve().parents[1]
directorio = raiz / "salida" / "experimentos" / "concurrencia_doble"
if args.modelo == "nvidia/nemotron-3.5-super-vl-120b-a12b":
    directorio = directorio / "nemotron_35_super_vl"
destino = directorio / f"{args.modo}_lote{args.tamano_lote}_{args.corrida:02d}.json"

if destino.exists() and not args.solo_validar:
    raise SystemExit(f"Ya existe {destino}. No se sobrescribirá.")

modelo = args.modelo
modos = {
    "base": (1, 1),
    "analisis": (2, 1),
    "generacion": (1, 2),
    "ambas": (2, 2),
}
trabajadores_analisis, trabajadores_generacion = modos[args.modo]

os.environ.update({
    "COMMUNITYLAB_CONCURRENCIA_MENSAJES": str(trabajadores_generacion),
    "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS": str(trabajadores_analisis),
    "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS": str(args.timeout_segundos),
    "COMMUNITYLAB_PROVEEDOR_ANALISIS": "nvidia_nim",
    "COMMUNITYLAB_PROVEEDOR_GENERACION": "nvidia_nim",
    "COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO": "true",
    "COMMUNITYLAB_MODELO_NVIDIA": modelo,
    "COMMUNITYLAB_MODELO_NVIDIA_RAPIDO": modelo,
    "COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR": modelo,
    "COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO": modelo,
})

if args.solo_validar:
    ruta_datos = raiz / "src/datos/mensajes_comunidad_simulados.json"
    contenido = ruta_datos.read_bytes()
    datos = json.loads(contenido.decode("utf-8"))
    total = sum(len(lote["interacciones"]) for lote in datos["lotes"])

    print("Modo:", args.modo)
    print("Trabajadores analisis:", trabajadores_analisis)
    print("Trabajadores generacion:", trabajadores_generacion)
    print("Tamano de lote:", args.tamano_lote)
    print("Mensajes del dataset:", total)
    print("SHA256:", hashlib.sha256(contenido).hexdigest())
    print("Modelo:", modelo)
    print("Timeout NVIDIA:", args.timeout_segundos, "s")
    print("Destino previsto:", destino)
    print("Destino existente:", destino.exists())
    print("Validacion sin llamadas LLM: OK")
    raise SystemExit(0)

from src.datos.entrega_ia import preparar_paquete_ia
from src.agentes.grafo import procesar_paquete_entrega
from src.agentes.entrega_resultados import preparar_entrega_resultados

ruta_datos = raiz / "src/datos/mensajes_comunidad_simulados.json"
contenido_datos = ruta_datos.read_bytes()
datos = json.loads(contenido_datos.decode("utf-8"))

paquete = preparar_paquete_ia(
    datos,
    fecha_referencia="2026-09-17T12:00:00Z",
    tamano_ciclo=20,
)

print("=== CAPTURA DE RESPUESTAS ===", flush=True)
print("Modo:", args.modo, flush=True)
print("Trabajadores analisis:", trabajadores_analisis, flush=True)
print("Trabajadores generacion:", trabajadores_generacion, flush=True)
print("Modelo:", modelo, flush=True)
print("Mensajes:", len(paquete["estados"]), flush=True)

inicio = time.perf_counter()
salida = procesar_paquete_entrega(
    paquete,
    tamano_lote=args.tamano_lote,
)
duracion = time.perf_counter() - inicio

resultados = salida["resultados"]

captura = {
    "protocolo": "comparacion_concurrencia_v2",
    "modo": args.modo,
    "corrida": args.corrida,
    "trabajadores_analisis": trabajadores_analisis,
    "trabajadores_generacion": trabajadores_generacion,
    "modelo": modelo,
    "timeout_segundos": args.timeout_segundos,
    "fecha_referencia": "2026-09-17T12:00:00Z",
    "tamano_ciclo": 20,
    "tamano_lote": args.tamano_lote,
    "sha256_dataset": hashlib.sha256(contenido_datos).hexdigest(),
    "id_ejecucion": salida["id_ejecucion"],
    "duracion_segundos": round(duracion, 2),
    "resultados": resultados,
    "ids_pendientes": salida.get("ids_pendientes", []),
}

try:
    captura["entrega"] = preparar_entrega_resultados(salida)
    captura["contrato_valido"] = True
except Exception as error:
    captura["contrato_valido"] = False
    captura["error_contrato_tipo"] = type(error).__name__

ids_esperados = [
    identificador
    for ciclo in paquete["plan"]["ciclos"]
    for identificador in ciclo["ids"]
]

ids_obtenidos = [r.get("id") for r in resultados]
errores_finales = sum(bool(r.get("errores")) for r in resultados)

captura["integridad"] = {
    "mensajes_esperados": len(ids_esperados),
    "mensajes_obtenidos": len(ids_obtenidos),
    "ids_en_orden": ids_obtenidos == ids_esperados,
    "ids_unicos": len(set(ids_obtenidos)) == len(ids_obtenidos),
    "pendientes_correctos": (
        salida.get("ids_pendientes", [])
        == paquete["plan"]["pendientes"]
    ),
    "errores_finales": errores_finales,
}

integridad = captura["integridad"]

captura["ejecucion_valida"] = all([
    captura["contrato_valido"],
    integridad["ids_en_orden"],
    integridad["ids_unicos"],
    integridad["pendientes_correctos"],
    errores_finales == 0,
])

eventos = []
ruta_log = raiz / "salida/logs/ciencia_datos.jsonl"

if ruta_log.exists():
    with ruta_log.open(encoding="utf-8") as archivo:
        for linea in archivo:
            try:
                evento = json.loads(linea)
                if evento.get("id_ejecucion") == salida["id_ejecucion"]:
                    eventos.append(evento)
            except json.JSONDecodeError:
                continue

proveedores = [
    e for e in eventos
    if e.get("evento") == "proveedor_ia_resuelto"
]

hay_eventos = bool(eventos)

captura["observabilidad"] = {
    "archivo_log_existe": ruta_log.is_file(),
    "eventos_ejecucion": len(eventos),
    "estado": (
        "eventos_encontrados"
        if hay_eventos
        else (
            "sin_eventos_ejecucion"
            if ruta_log.is_file()
            else "archivo_ausente"
        )
    ),
    "errores_llm": (
        sum(e.get("evento") == "llm_error" for e in eventos)
        if hay_eventos else None
    ),
    "reintentos": (
        sum(e.get("evento") == "reintento_programado" for e in eventos)
        if hay_eventos else None
    ),
    "fallbacks": (
        sum(bool(e.get("fallback_activado")) for e in proveedores)
        if hay_eventos else None
    ),
    "proveedores": (
        dict(Counter(
            e.get("proveedor_usado") for e in proveedores
        ))
        if hay_eventos else None
    ),
}

directorio.mkdir(parents=True, exist_ok=True)
destino.write_text(
    json.dumps(captura, ensure_ascii=False, indent=4),
    encoding="utf-8",
)

print("\n=== RESULTADO ===")
print("Tiempo:", captura["duracion_segundos"], "s")
print("Mensajes:", len(resultados))
print("Activos:", sum(
    len(r.get("activos_generados") or {}) for r in resultados
))
print("Errores finales:", sum(bool(r.get("errores")) for r in resultados))
print("Contrato valido:", captura["contrato_valido"])
print("Observabilidad:", captura["observabilidad"])
print("SHA256 dataset:", captura["sha256_dataset"])
print("Archivo:", destino)
print("Integridad:", captura["integridad"])
print("Ejecucion valida:", captura["ejecucion_valida"])

if not captura["ejecucion_valida"]:
    raise SystemExit(
        "Benchmark con anomalías: revisar el archivo JSON."
    )
