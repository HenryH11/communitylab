"""QA-2: Medir latencia por mensaje en el pipeline IA (Semana 5.1).

Mide tiempo de análisis y de generación por separado. Sin red: requiere .env con keys.
"""
import json
import statistics
import time
from pathlib import Path

from dotenv import load_dotenv

from src.agentes.grafo import procesar_paquete_entrega
from src.datos.entrega_ia import preparar_paquete_ia

FECHA_REF = "2026-10-18T12:00:00Z"
DATASET = Path("src/datos/mensajes_comunidad_simulados.json")
SALIDA = Path("reports/latencia_semana51.json")


def main() -> None:
    load_dotenv()
    datos = json.loads(DATASET.read_text(encoding="utf-8"))

    paquete = preparar_paquete_ia(datos, fecha_referencia=FECHA_REF, tamano_ciclo=20)
    ids = [i["id"] for i in paquete.get("interacciones", [])]

    inicio = time.perf_counter()
    resultado = procesar_paquete_entrega(paquete)
    total = time.perf_counter() - inicio

    por_id = resultado.get("resultados_por_id", {})
    tiempos = []

    for id_msg in ids:
        data = por_id.get(id_msg, {})
        # El pipeline no expone tiempo por ID directamente; aproximamos
        # con métricas internas si existen, o marcamos None.
        t = data.get("tiempo_ms") or data.get("latencia_ms")
        tiempos.append({"id": id_msg, "tiempo_ms": t,
                        "rutas": data.get("rutas", []),
                        "activos": list(data.get("activos_generados", {}).keys())})

    medidos = [t["tiempo_ms"] for t in tiempos if t["tiempo_ms"] is not None]

    reporte = {
        "fecha": "2026-10-18",
        "total_mensajes": len(ids),
        "tiempo_total_seg": round(total, 2),
        "promedio_ms": round(statistics.mean(medidos), 1) if medidos else None,
        "mediana_ms": round(statistics.median(medidos), 1) if medidos else None,
        "max_ms": max(medidos) if medidos else None,
        "min_ms": min(medidos) if medidos else None,
        "por_mensaje": tiempos,
        "nota": "Si promedio_ms es null, el pipeline aún no expone tiempo por ID. "
                "Registrar tiempo total / cantidad de mensajes como aproximación.",
    }

    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text(json.dumps(reporte, ensure_ascii=False, indent=4), encoding="utf-8")
    print(f"✅ Reporte escrito en {SALIDA}")
    print(f"   Total: {total:.2f}s / {len(ids)} mensajes → {total/len(ids):.2f}s prom.")


if __name__ == "__main__":
    main()