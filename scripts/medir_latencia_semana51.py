"""QA-2: Medir latencia por mensaje en el pipeline IA (Semana 5.1).

Mide tiempo total, promedio, mediana, mínimo y máximo por mensaje.
Soporta la estructura actual del dataset (metadata + lotes) y la clave
`estados` que devuelve preparar_paquete_ia().

Uso:
    python scripts/medir_latencia_semana51.py

Requiere:
    - .env con GEMINI_API_KEY o NVIDIA_API_KEY configuradas
    - src/datos/mensajes_comunidad_simulados.json

Salida:
    reports/latencia_semana51.json
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Fix de sys.path: permite ejecutar el script directamente
#   python scripts/medir_latencia_semana51.py
# sin que falle con "ModuleNotFoundError: No module named 'src'".
# ---------------------------------------------------------------------------
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

from dotenv import load_dotenv  # noqa: E402

from src.agentes.grafo import procesar_paquete_entrega  # noqa: E402
from src.datos.entrega_ia import preparar_paquete_ia  # noqa: E402

FECHA_REF = "2026-10-18T12:00:00Z"
DATASET = _RAIZ / "src" / "datos" / "mensajes_comunidad_simulados.json"
SALIDA = _RAIZ / "reports" / "latencia_semana51.json"


def _cargar_dataset() -> dict:
    """Carga el dataset simulado desde disco."""
    if not DATASET.exists():
        raise FileNotFoundError(f"No se encontró el dataset: {DATASET}")
    return json.loads(DATASET.read_text(encoding="utf-8"))


def _contar_interacciones(datos) -> tuple[int, str]:
    """Cuenta interacciones soportando lista directa, interacciones o lotes.

    Devuelve (cantidad, descripcion_estructura).
    """
    if isinstance(datos, list):
        return len(datos), "lista directa"

    if isinstance(datos, dict):
        # Estructura vieja: interacciones directas
        if isinstance(datos.get("interacciones"), list):
            return len(datos["interacciones"]), "dict -> interacciones"

        # Estructura nueva: metadata + lotes
        if isinstance(datos.get("lotes"), list):
            total = sum(
                len(lote.get("interacciones", []))
                for lote in datos["lotes"]
                if isinstance(lote, dict)
            )
            return total, f"dict -> lotes ({len(datos['lotes'])} lotes)"

    return 0, "estructura desconocida"


def _ids_desde_estados(paquete) -> list[str]:
    """Extrae los IDs de los mensajes desde paquete['estados'].

    Soporta que 'estados' sea un dict (id -> estado) o una lista de dicts
    con campo 'id'. Es la clave real que devuelve preparar_paquete_ia()
    en la versión actual de develop.
    """
    if not isinstance(paquete, dict):
        return []

    estados = paquete.get("estados")
    if isinstance(estados, dict):
        return list(estados.keys())

    if isinstance(estados, list):
        ids: list[str] = []
        for item in estados:
            if isinstance(item, dict):
                id_val = (
                    item.get("id")
                    or item.get("id_mensaje")
                    or item.get("interaccion_id")
                )
                if id_val:
                    ids.append(str(id_val))
            elif isinstance(item, str):
                ids.append(item)
        return ids

    return []


def _extraer_tiempo_por_id(data: dict) -> float | None:
    """Busca campos de tiempo en el resultado por ID. None si no existe."""
    if not isinstance(data, dict):
        return None
    for clave in ("tiempo_ms", "latencia_ms", "duracion_ms", "tiempo_total_ms"):
        valor = data.get(clave)
        if isinstance(valor, (int, float)):
            return float(valor)
    return None


def main() -> None:
    print("=" * 70)
    print("QA-2 — Medición de latencia por mensaje (Semana 5.1)")
    print("=" * 70)

    load_dotenv()

    print(f"Dataset:  {DATASET}")
    print(f"Salida:   {SALIDA}")
    print(f"Provider: {__import__('os').getenv('COMMUNITYLAB_PROVEEDOR_GENERACION', 'default')}")
    print("-" * 70)

    datos = _cargar_dataset()
    n_dataset, estructura = _contar_interacciones(datos)
    print(f"[1/3] Dataset cargado: {n_dataset} interacciones ({estructura})")

    if n_dataset == 0:
        print("⚠️  Dataset sin interacciones. Abortando.")
        sys.exit(1)

    print("[2/3] Preparando paquete IA...")
    paquete = preparar_paquete_ia(datos, fecha_referencia=FECHA_REF, tamano_ciclo=20)

    ids = _ids_desde_estados(paquete)
    print(f"      Paquete listo: {len(ids)} mensajes en 'estados'")

    if len(ids) == 0:
        print("⚠️  No se pudieron extraer IDs de 'estados'. Abortando.")
        sys.exit(1)

    print("[3/3] Procesando con IA (esto tarda 2–4 min)...")
    inicio = time.perf_counter()
    resultado = procesar_paquete_entrega(paquete)
    total_seg = time.perf_counter() - inicio
    print(f"      Procesamiento completado en {total_seg:.2f}s")

    por_id = resultado.get("resultados_por_id", {}) if isinstance(resultado, dict) else {}
    registros: list[dict] = []
    tiempos: list[float] = []

    for id_msg in ids:
        data = por_id.get(id_msg, {}) or {}
        t_ms = _extraer_tiempo_por_id(data)
        if t_ms is not None:
            tiempos.append(t_ms)
        registros.append(
            {
                "id": id_msg,
                "tiempo_ms": t_ms,
                "rutas": list(data.get("rutas", []) or []),
                "activos": list((data.get("activos_generados") or {}).keys()),
                "errores": list(data.get("errores", []) or []),
                "fallos": list(data.get("fallos", []) or []),
            }
        )

    nota = None
    if tiempos:
        promedio_ms = round(statistics.mean(tiempos), 1)
        mediana_ms = round(statistics.median(tiempos), 1)
        minimo_ms = round(min(tiempos), 1)
        maximo_ms = round(max(tiempos), 1)
    else:
        promedio_ms = round((total_seg * 1000) / max(len(ids), 1), 1)
        mediana_ms = None
        minimo_ms = None
        maximo_ms = None
        nota = (
            "El pipeline no expone tiempo_ms por ID. Se registra el promedio "
            "calculado como tiempo_total / cantidad de mensajes procesados. "
            "Para medir por mensaje real, DS debe agregar el campo tiempo_ms al resultado."
        )

    reporte = {
        "fecha": "2026-10-18",
        "rama": "feature/streamlit-agente-vivo-semana5.1",
        "dataset": str(DATASET.relative_to(_RAIZ)).replace("\\", "/"),
        "estructura_dataset": estructura,
        "total_mensajes_dataset": n_dataset,
        "total_mensajes_procesados": len(ids),
        "tiempo_total_seg": round(total_seg, 2),
        "promedio_ms": promedio_ms,
        "mediana_ms": mediana_ms,
        "minimo_ms": minimo_ms,
        "maximo_ms": maximo_ms,
        "por_mensaje": registros,
        "nota": nota,
    }

    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    SALIDA.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )

    print("-" * 70)
    print(f"✅ Reporte escrito en {SALIDA}")
    print(f"   Dataset:    {n_dataset} interacciones")
    print(f"   Procesados: {len(ids)}")
    print(f"   Total:      {total_seg:.2f}s")
    if promedio_ms:
        print(f"   Promedio:   {promedio_ms} ms/mensaje")
    if mediana_ms is not None:
        print(f"   Mediana:    {mediana_ms} ms")
        print(f"   Mín/Máx:    {minimo_ms} / {maximo_ms} ms")
    if nota:
        print(f"   ⚠️  {nota}")


if __name__ == "__main__":
    main()