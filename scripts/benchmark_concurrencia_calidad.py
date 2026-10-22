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
    choices=("secuencial", "concurrente"),
    required=True,
)
parser.add_argument("--corrida", type=int, default=1)
args = parser.parse_args()

if args.corrida < 1:
    parser.error("--corrida debe ser mayor que cero")

raiz = Path(__file__).resolve().parents[1]
directorio = raiz / "salida" / "experimentos" / "concurrencia_calidad"
destino = directorio / f"{args.modo}_{args.corrida:02d}.json"

if destino.exists():
    raise SystemExit(f"Ya existe {destino}. No se sobrescribirá.")

modelo = "nvidia/nemotron-3-super-120b-a12b"
trabajadores = 1 if args.modo == "secuencial" else 2

os.environ.update({
    "COMMUNITYLAB_CONCURRENCIA_MENSAJES": str(trabajadores),
    "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS": "1",
    "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS": "30",
    "COMMUNITYLAB_PROVEEDOR_ANALISIS": "nvidia_nim",
    "COMMUNITYLAB_PROVEEDOR_GENERACION": "nvidia_nim",
    "COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO": "true",
    "COMMUNITYLAB_MODELO_NVIDIA": modelo,
    "COMMUNITYLAB_MODELO_NVIDIA_RAPIDO": modelo,
    "COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR": modelo,
    "COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO": modelo,
})

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
print("Trabajadores:", trabajadores, flush=True)
print("Modelo:", modelo, flush=True)
print("Mensajes:", len(paquete["estados"]), flush=True)

inicio = time.perf_counter()
salida = procesar_paquete_entrega(paquete)
duracion = time.perf_counter() - inicio

resultados = salida["resultados"]

captura = {
    "protocolo": "comparacion_concurrencia_v1",
    "modo": args.modo,
    "corrida": args.corrida,
    "trabajadores": trabajadores,
    "modelo": modelo,
    "timeout_segundos": 30,
    "fecha_referencia": "2026-09-17T12:00:00Z",
    "tamano_ciclo": 20,
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

captura["observabilidad"] = {
    "errores_llm": sum(
        e.get("evento") == "llm_error" for e in eventos
    ),
    "reintentos": sum(
        e.get("evento") == "reintento_programado" for e in eventos
    ),
    "fallbacks": sum(
        bool(e.get("fallback_activado")) for e in proveedores
    ),
    "proveedores": dict(Counter(
        e.get("proveedor_usado") for e in proveedores
    )),
}

directorio.mkdir(parents=True, exist_ok=True)
destino.write_text(
    json.dumps(captura, ensure_ascii=False, indent=2),
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
