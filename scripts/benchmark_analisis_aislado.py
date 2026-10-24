import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument(
    "--modo",
    choices=("secuencial", "concurrente"),
    required=True,
)
parser.add_argument("--tamano-lote", type=int, default=6)
parser.add_argument("--corrida", type=int, default=1)
parser.add_argument("--solo-validar", action="store_true")
args = parser.parse_args()

if not 1 <= args.tamano_lote <= 10:
    parser.error("--tamano-lote debe estar entre 1 y 10")
if args.corrida < 1:
    parser.error("--corrida debe ser mayor que cero")

raiz = Path(__file__).resolve().parents[1]
carpeta = raiz / "salida/experimentos/analisis_aislado"
destino = carpeta / (
    f"{args.modo}_lote{args.tamano_lote}_{args.corrida:02d}.json"
)

if destino.exists() and not args.solo_validar:
    raise SystemExit(f"El archivo ya existe: {destino}")

trabajadores = 1 if args.modo == "secuencial" else 2
modelo = "nvidia/nemotron-3-super-120b-a12b"

os.environ.update({
    "COMMUNITYLAB_CONCURRENCIA_LOTES_ANALISIS": str(trabajadores),
    "COMMUNITYLAB_CONCURRENCIA_MENSAJES": "1",
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
from src.agentes.procesamiento import procesar_paquete_entrega

ruta_datos = raiz / "src/datos/mensajes_comunidad_simulados.json"
contenido = ruta_datos.read_bytes()
datos = json.loads(contenido.decode("utf-8"))

paquete = preparar_paquete_ia(
    datos,
    fecha_referencia="2026-09-17T12:00:00Z",
    tamano_ciclo=20,
)

print("Modo:", args.modo)
print("Trabajadores de análisis:", trabajadores)
print("Tamaño de lote:", args.tamano_lote)
print("Mensajes:", len(paquete["estados"]))
print(
    "Ciclos:",
    [c["cantidad"] for c in paquete["plan"]["ciclos"]]
)
print("Modelo:", modelo)

if args.solo_validar:
    print("Validación sin llamadas LLM: OK")
    raise SystemExit(0)

# Desactiva solamente la etapa de enrutamiento y generación.
# El análisis real y su concurrencia siguen ejecutándose.
with patch(
    "src.agentes.grafo.grafo_desde_analisis.invoke",
    side_effect=lambda estado: estado,
):
    inicio = time.perf_counter()
    salida = procesar_paquete_entrega(
        paquete,
        tamano_lote=args.tamano_lote,
        pasadas_recuperacion=0,
    )
    duracion = time.perf_counter() - inicio

resultados = salida["resultados"]
ids_esperados = [
    identificador
    for ciclo in paquete["plan"]["ciclos"]
    for identificador in ciclo["ids"]
]
ids_obtenidos = [r["id"] for r in resultados]

assert ids_obtenidos == ids_esperados, "Error de integridad de IDs"

captura = {
    "protocolo": "analisis_aislado_v1",
    "modo": args.modo,
    "corrida": args.corrida,
    "trabajadores_analisis": trabajadores,
    "tamano_lote": args.tamano_lote,
    "modelo": modelo,
    "sha256_dataset": hashlib.sha256(contenido).hexdigest(),
    "duracion_segundos": round(duracion, 2),
    "id_ejecucion": salida["id_ejecucion"],
    "generacion_omitida": True,
    "recuperacion_posterior_omitida": True,
    "resultados": resultados,
}

carpeta.mkdir(parents=True, exist_ok=True)
destino.write_text(
    json.dumps(captura, ensure_ascii=False, indent=4),
    encoding="utf-8",
)

print("\\n=== RESULTADO ===")
print("Tiempo:", captura["duracion_segundos"], "s")
print("Mensajes:", len(resultados))
print("Errores:", sum(bool(r.get("errores")) for r in resultados))
print("Archivo:", destino)
