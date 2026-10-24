"""Compara modelos candidatos para el agente en vivo sobre su flujo real.

Cada modelo se ejecuta en un subproceso propio y sin respaldo a Gemini, para que
las métricas reflejen solo a ese modelo. Se usan los mismos filtros, búsqueda,
validación de citas y verificación que el agente en producción.

Uso:
    python -m scripts.comparar_modelos_agente
    python -m scripts.comparar_modelos_agente --modelos nvidia/x gemini:gemini-3.5-flash-lite
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

RUTA_DATOS = RAIZ / "docs/evidencia2_entrega_ciencia_datos_completa.json"
CARPETA_SALIDA = RAIZ / "salida/experimentos/comparacion_modelos_agente"

MODELOS_POR_DEFECTO = (
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3.5-super-vl-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3.5-bolt-e4b",
    "minimaxai/minimax-m3.1-flash",
    "meta/muse-glimmer-30b",
    "stepfun-ai/step-5-preview",
    "z-ai/glm-5.3",
    "openai/gpt-oss-20b",
    "gemini:gemini-3.5-flash-lite",
)

# (consulta, modo de verificación, plataforma esperada o None si es analítica)
CASOS: tuple[tuple[str, str, str | None], ...] = (
    ("¿Qué opina la comunidad sobre la mentoría y el aprendizaje?", "prompt_estricto", None),
    ("Dame los testimonios sobre empleabilidad", "prompt_estricto", None),
    ("¿Qué dudas técnicas tienen sobre LangGraph?", "prompt_estricto", None),
    ("Resume el sentimiento de los mensajes de Discord", "prompt_estricto", None),
    ("Escribe un post de LinkedIn con testimonios de empleabilidad", "prompt_estricto", "linkedin"),
    ("Haz un post para Instagram con los testimonios más positivos", "prompt_estricto", "instagram"),
    ("Crea un tuit sobre la mentoría", "prompt_estricto", "x"),
    ("Escribe un post de LinkedIn sobre los testimonios", "verificacion_automatica", "linkedin"),
)


def _ejecutar_modelo(modelo: str, repeticiones: int = 1) -> list[dict[str, Any]]:
    """Corre todos los casos con un único modelo, sin respaldo entre proveedores."""
    from src.agentes import conversacion
    from src.agentes.configuracion_ia import PROVEEDOR_GEMINI, PROVEEDOR_NVIDIA_NIM
    from src.agentes.modelo_ia import obtener_modelo_generacion_estructurado
    from src.agentes.prompts.conversacion import prompt_conversacion
    from src.agentes.prompts.verificacion import prompt_verificacion

    if modelo.startswith("gemini:"):
        os.environ["COMMUNITYLAB_MODELO_GEMINI"] = modelo.split(":", 1)[1]
        proveedor, modelo_id = PROVEEDOR_GEMINI, None
    else:
        proveedor, modelo_id = PROVEEDOR_NVIDIA_NIM, modelo

    llamadas = {"total": 0}

    def contar(cadena):
        def invocar(entrada, config=None):
            llamadas["total"] += 1
            return cadena.invoke(entrada, config=config)

        return type("Cadena", (), {"invoke": staticmethod(invocar)})()

    cadena_generacion = contar(prompt_conversacion | obtener_modelo_generacion_estructurado(
        conversacion.SalidaConversacional, proveedor=proveedor, modelo=modelo_id,
    ))
    cadena_verificacion = contar(prompt_verificacion | obtener_modelo_generacion_estructurado(
        conversacion.SalidaVerificacion, proveedor=proveedor, modelo=modelo_id,
    ))
    # Un proveedor ficticio evita la rama con respaldo y fuerza el modelo elegido.
    conversacion.obtener_proveedor_generacion = lambda: "comparacion"
    conversacion._obtener_cadena = lambda _proveedor: cadena_generacion
    conversacion._obtener_cadena_verificacion = lambda _proveedor: cadena_verificacion

    datos = json.loads(RUTA_DATOS.read_text(encoding="utf-8"))
    resultados = []
    for consulta, modo, plataforma in CASOS * repeticiones:
        agente = conversacion.AgenteConversacional(datos)
        llamadas["total"] = 0
        inicio = time.perf_counter()
        registro: dict[str, Any] = {"consulta": consulta, "modo": modo, "plataforma_esperada": plataforma}
        try:
            salida = agente.consultar(consulta, modo_verificacion=modo)
            registro.update(
                exito=True,
                respuesta=salida["respuesta"],
                citas=salida["citas"],
                borrador=salida["borrador"],
                verificacion=salida["verificacion"]["estado"],
                coincidencias=salida["total_coincidencias"],
            )
        except Exception as error:  # noqa: BLE001 - se registra cualquier fallo del modelo
            registro.update(exito=False, error=f"{type(error).__name__}: {error}"[:300])
        registro["segundos"] = round(time.perf_counter() - inicio, 2)
        registro["llamadas"] = llamadas["total"]
        registro["cumple"] = _cumple(registro)
        resultados.append(registro)
    return resultados


def _cumple(registro: dict[str, Any]) -> bool:
    """Revisa el contrato observable del caso, no el estilo de la respuesta."""
    if not registro.get("exito") or not registro.get("coincidencias"):
        return False
    if not registro.get("citas"):
        return False
    plataforma = registro["plataforma_esperada"]
    if plataforma is None:
        return bool(registro["respuesta"].strip())
    borrador = registro.get("borrador")
    if not borrador or borrador["plataforma"] != plataforma:
        return False
    if plataforma == "x" and len(borrador["contenido"]) > 280:
        return False
    if registro["modo"] == "verificacion_automatica":
        return registro.get("verificacion") == "verificado"
    return True


def _resumen(modelo: str, resultados: list[dict[str, Any]]) -> dict[str, Any]:
    tiempos = [r["segundos"] for r in resultados if r["exito"]]
    return {
        "modelo": modelo,
        "casos": len(resultados),
        "exitos": sum(r["exito"] for r in resultados),
        "cumple": sum(r["cumple"] for r in resultados),
        "mediana_segundos": round(statistics.median(tiempos), 1) if tiempos else None,
        "maximo_segundos": round(max(tiempos), 1) if tiempos else None,
    }


def _lanzar(modelo: str, timeout: float, repeticiones: int) -> dict[str, Any]:
    nombre = modelo.replace("/", "__").replace(":", "_")
    archivo = CARPETA_SALIDA / f"{nombre}.json"
    entorno = {**os.environ, "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS": str(timeout), "PYTHONIOENCODING": "utf-8"}
    proceso = subprocess.run(
        [
            sys.executable, "-m", "scripts.comparar_modelos_agente",
            "--trabajador", modelo, "--archivo", str(archivo), "--repeticiones", str(repeticiones),
        ],
        cwd=RAIZ, env=entorno, capture_output=True, text=True, encoding="utf-8",
    )
    if proceso.returncode != 0 or not archivo.exists():
        return {"modelo": modelo, "error": proceso.stderr[-500:]}
    return json.loads(archivo.read_text(encoding="utf-8"))["resumen"]


def principal() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    parser.add_argument("--modelos", nargs="+", default=list(MODELOS_POR_DEFECTO))
    parser.add_argument("--paralelo", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--repeticiones", type=int, default=1)
    parser.add_argument("--trabajador", help=argparse.SUPPRESS)
    parser.add_argument("--archivo", type=Path, help=argparse.SUPPRESS)
    argumentos = parser.parse_args()

    if argumentos.trabajador:
        resultados = _ejecutar_modelo(argumentos.trabajador, argumentos.repeticiones)
        argumentos.archivo.write_text(
            json.dumps(
                {"resumen": _resumen(argumentos.trabajador, resultados), "resultados": resultados},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return 0

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(argumentos.paralelo) as ejecutor:
        resumenes = list(ejecutor.map(
            lambda m: _lanzar(m, argumentos.timeout, argumentos.repeticiones), argumentos.modelos,
        ))
    resumenes.sort(key=lambda r: (-r.get("cumple", -1), r.get("mediana_segundos") or 1e9))
    (CARPETA_SALIDA / "resumen.json").write_text(json.dumps(resumenes, ensure_ascii=False, indent=2), encoding="utf-8")
    for r in resumenes:
        if "error" in r:
            print(f"{r['modelo']:45} ERROR {r['error'][-160:]}")
        else:
            print(
                f"{r['modelo']:45} cumple {r['cumple']}/{r['casos']}  éxito {r['exitos']}/{r['casos']}  "
                f"mediana {r['mediana_segundos']}s  máx {r['maximo_segundos']}s"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
