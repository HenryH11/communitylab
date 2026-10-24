"""Evalúa múltiples modelos de NVIDIA NIM sobre el holdout de 30 casos corregidos.

Genera métricas detalladas por modelo, comparativa global, y guarda
todos los artefactos en salida/experimentos/comparacion_modelos_nvidia/.
"""

import json
import os
import time
from collections import defaultdict
from pathlib import Path

import dotenv
from langchain_openai import ChatOpenAI

from src.agentes.modelos import AnalisisLote
from src.agentes.prompts.analisis import template_analisis_lote
from src.agentes.proveedores.nvidia_nim import _agregar_instruccion_esquema

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE_PATH = (
    RAIZ
    / "salida"
    / "experimentos"
    / "holdout_texto_corregido_fixture_v1.json"
)
DIR_SALIDA = (
    RAIZ / "salida" / "experimentos" / "comparacion_modelos_nvidia"
)
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

DIMENSIONES = {
    "sentimiento": "sentimiento_esperado",
    "tema_principal": "tema_esperado",
    "tipo_detectado": "tipo_esperado",
}

# Modelos candidatos seleccionados tras la exploración del catálogo accesible
MODELOS_CANDIDATOS = [
    {
        "id": "nvidia/nemotron-3.5-lightning-30b-a3b",
        "nombre": "Nemotron 3.5 Lightning 30B (Línea base actual)",
        "param_extra": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    {
        "id": "nvidia/nemotron-3-super-120b-a12b",
        "nombre": "Nemotron 3 Super 120B (MoE 12B activo)",
        "param_extra": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    {
        "id": "nvidia/nemotron-3-ultra-550b-a55b",
        "nombre": "Nemotron 3 Ultra 550B (MoE 55B activo)",
        "param_extra": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    {
        "id": "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        "nombre": "Nemotron 3 Nano Omni Reasoning 30B",
        "param_extra": {},
    },
    {
        "id": "openai/gpt-oss-20b",
        "nombre": "OpenAI GPT-OSS 20B",
        "param_extra": {},
    },
    {
        "id": "moonshotai/kimi-k3",
        "nombre": "Moonshot AI Kimi K3",
        "param_extra": {},
    },
    {
        "id": "google/gemma-4-31b-it",
        "nombre": "Google Gemma 4 31B Instruct",
        "param_extra": {},
    },
    {
        "id": "z-ai/glm-5.3-flash",
        "nombre": "Zhipu AI GLM 5.3 Flash",
        "param_extra": {},
    },
]


def evaluar_resultados_caso(
    casos: list[dict], resultados: dict[str, dict]
) -> dict:
    metricas = {}
    for campo_predicho, campo_esperado in DIMENSIONES.items():
        correctos = 0
        por_clase = defaultdict(lambda: {"correctos": 0, "total": 0})
        for caso in casos:
            esperado = caso[campo_esperado]
            obtenido = resultados[caso["id"]].get(campo_predicho)
            por_clase[esperado]["total"] += 1
            if obtenido == esperado:
                correctos += 1
                por_clase[esperado]["correctos"] += 1

        metricas[campo_predicho] = {
            "correctos": correctos,
            "total": len(casos),
            "accuracy": round(correctos / len(casos), 4),
            "por_clase": dict(por_clase),
        }

    triples = sum(
        all(
            resultados[caso["id"]].get(campo_predicho)
            == caso[campo_esperado]
            for campo_predicho, campo_esperado in DIMENSIONES.items()
        )
        for caso in casos
    )
    metricas["triple_correcto"] = {
        "correctos": triples,
        "total": len(casos),
        "accuracy": round(triples / len(casos), 4),
    }
    return metricas


def invocar_lote(
    client: ChatOpenAI,
    lote: list[dict],
    max_intentos: int = 3,
    pausa: float = 3.0,
) -> tuple[list[dict], float, int]:
    mensajes = [
        {
            "id": c["id"],
            "origen": c["origen"],
            "canal": c["canal"],
            "idioma": c["idioma"],
            "texto": c["texto"],
        }
        for c in lote
    ]

    prompt = template_analisis_lote.invoke(
        {"mensajes_json": json.dumps(mensajes, ensure_ascii=False)}
    )
    preparado = _agregar_instruccion_esquema(prompt, AnalisisLote)

    reintentos = 0
    for intento in range(1, max_intentos + 1):
        t0 = time.perf_counter()
        try:
            resp = client.invoke(preparado)
            elapsed = time.perf_counter() - t0
            parsed = AnalisisLote.model_validate_json(resp.content)
            
            ids_esperados = {c["id"] for c in lote}
            ids_recibidos = {r.id for r in parsed.resultados}
            if ids_esperados != ids_recibidos:
                raise ValueError(
                    f"IDs devueltos no coinciden con el lote: {ids_recibidos ^ ids_esperados}"
                )
            
            return [r.model_dump() for r in parsed.resultados], elapsed, reintentos
        except Exception as e:
            elapsed = time.perf_counter() - t0
            reintentos += 1
            print(f"    Intento {intento}/{max_intentos} falló ({elapsed:.1f}s): {type(e).__name__}: {str(e)[:100]}", flush=True)
            if intento < max_intentos:
                time.sleep(pausa)

    raise RuntimeError("Lote agotó todos los intentos.")


def main():
    dotenv.load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("No se encontró NVIDIA_API_KEY en el entorno.")

    with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
        fixture = json.load(f)
    casos = fixture["casos"]
    print(f"Cargados {len(casos)} casos del fixture {FIXTURE_PATH.name}", flush=True)

    DIR_SALIDA.mkdir(parents=True, exist_ok=True)
    resumen_global = []

    for cfg in MODELOS_CANDIDATOS:
        model_id = cfg["id"]
        nombre = cfg["nombre"]
        param_extra = cfg.get("param_extra", {})

        print("\n" + "=" * 80, flush=True)
        print(f"Evaluando modelo: {nombre} ({model_id})", flush=True)
        print("=" * 80, flush=True)

        try:
            client = ChatOpenAI(
                api_key=api_key,
                base_url=NVIDIA_BASE_URL,
                model=model_id,
                temperature=0,
                timeout=60,
                max_retries=0,
                extra_body=param_extra,
            ).bind(response_format={"type": "json_object"})
        except Exception as e:
            print(f"ERROR creando cliente para {model_id}: {e}", flush=True)
            continue

        tamano_lote = 10
        resultados_dict = {}
        tiempos_lote = []
        total_reintentos = 0
        modelo_fallo = False

        t_inicio_modelo = time.perf_counter()

        for inicio in range(0, len(casos), tamano_lote):
            lote = casos[inicio : inicio + tamano_lote]
            num_lote = (inicio // tamano_lote) + 1
            print(f"  Procesando lote {num_lote} (casos {inicio+1}-{min(inicio+tamano_lote, len(casos))})...", end="", flush=True)

            try:
                resultados_lote, elapsed, retries = invocar_lote(client, lote)
                tiempos_lote.append(elapsed)
                total_reintentos += retries
                for r in resultados_lote:
                    resultados_dict[r["id"]] = r
                print(f" OK ({elapsed:.1f}s)", flush=True)
            except Exception as e:
                print(f" FALLÓ LOTE {num_lote}: {e}", flush=True)
                modelo_fallo = True
                break

        if modelo_fallo or len(resultados_dict) != len(casos):
            print(f"El modelo {model_id} no completó la evaluación.", flush=True)
            continue

        duracion_total = round(time.perf_counter() - t_inicio_modelo, 2)
        metricas = evaluar_resultados_caso(casos, resultados_dict)

        print(f"\nResultados {nombre}:", flush=True)
        print(f"  Sentimiento:     {metricas['sentimiento']['correctos']}/{len(casos)} ({metricas['sentimiento']['accuracy']*100:.1f}%)", flush=True)
        print(f"  Tema principal:  {metricas['tema_principal']['correctos']}/{len(casos)} ({metricas['tema_principal']['accuracy']*100:.1f}%)", flush=True)
        print(f"  Tipo detectado:  {metricas['tipo_detectado']['correctos']}/{len(casos)} ({metricas['tipo_detectado']['accuracy']*100:.1f}%)", flush=True)
        print(f"  Triple exacto:   {metricas['triple_correcto']['correctos']}/{len(casos)} ({metricas['triple_correcto']['accuracy']*100:.1f}%)", flush=True)
        print(f"  Tiempo total:    {duracion_total}s (promedio lote: {sum(tiempos_lote)/len(tiempos_lote):.1f}s)", flush=True)

        nombre_archivo = model_id.replace("/", "_")
        ruta_detalle = DIR_SALIDA / f"detalle_{nombre_archivo}.json"
        with open(ruta_detalle, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "modelo_id": model_id,
                    "nombre": nombre,
                    "metricas": metricas,
                    "duracion_total_s": duracion_total,
                    "tiempos_lote_s": tiempos_lote,
                    "reintentos": total_reintentos,
                    "predicciones": resultados_dict,
                },
                f,
                ensure_ascii=False,
                indent=4,
            )

        resumen_global.append(
            {
                "modelo_id": model_id,
                "nombre": nombre,
                "sentimiento_acc": metricas["sentimiento"]["accuracy"],
                "sentimiento_correctos": metricas["sentimiento"]["correctos"],
                "tema_acc": metricas["tema_principal"]["accuracy"],
                "tema_correctos": metricas["tema_principal"]["correctos"],
                "tipo_acc": metricas["tipo_detectado"]["accuracy"],
                "tipo_correctos": metricas["tipo_detectado"]["correctos"],
                "triple_acc": metricas["triple_correcto"]["accuracy"],
                "triple_correctos": metricas["triple_correcto"]["correctos"],
                "duracion_total_s": duracion_total,
                "reintentos": total_reintentos,
            }
        )

    # Ordenar por triple_correcto desc, luego por sentimiento desc, luego por tiempo asc
    resumen_global.sort(
        key=lambda x: (x["triple_correctos"], x["sentimiento_correctos"], -x["duracion_total_s"]),
        reverse=True,
    )

    ruta_comparativa = DIR_SALIDA / "comparativa_modelos_nvidia.json"
    with open(ruta_comparativa, "w", encoding="utf-8") as f:
        json.dump(resumen_global, f, ensure_ascii=False, indent=4)

    print("\n" + "=" * 80, flush=True)
    print("TABLA COMPARATIVA FINAL:", flush=True)
    print("=" * 80, flush=True)
    print(f"{'Modelo':<45} | {'Triple':<10} | {'Sent.':<8} | {'Tema':<8} | {'Tipo':<8} | {'Tiempo':<8}", flush=True)
    print("-" * 95, flush=True)
    for r in resumen_global:
        print(
            f"{r['modelo_id']:<45} | "
            f"{r['triple_correctos']}/30 ({r['triple_acc']*100:.0f}%) | "
            f"{r['sentimiento_correctos']}/30 | "
            f"{r['tema_correctos']}/30 | "
            f"{r['tipo_correctos']}/30 | "
            f"{r['duracion_total_s']}s",
            flush=True,
        )

    print(f"\nResultados guardados en {DIR_SALIDA}", flush=True)


if __name__ == "__main__":
    main()
