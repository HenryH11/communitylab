"""Benchmark exploratorio de calibración semántica entre NVIDIA NIM y Gemini.

Los casos incluidos son ejemplos ambiguos para comparación cualitativa.
No constituyen ground truth humano ni se utilizan para calcular accuracy
ni para declarar superioridad de un proveedor.

El benchmark utiliza un timeout ampliado para NVIDIA únicamente dentro
de este proceso experimental. No modifica la configuración productiva
del proyecto.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv


RAIZ = Path(__file__).resolve().parent.parent

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

load_dotenv(override=True)


from src.agentes.configuracion_ia import (
    TIER_ESTANDAR,
    obtener_modelo_nvidia_por_tier,
)
from src.agentes.modelo_ia import (
    obtener_modelo_analisis_estructurado,
)
from src.agentes.modelos import AnalisisMensaje
from src.agentes.prompts.analisis import template_analisis
from src.agentes.proveedores.gemini import MODELO_GEMINI


# Timeout experimental exclusivo de este benchmark.
# La configuración productiva de CommunityLab no se modifica.
TIMEOUT_NVIDIA_BENCHMARK_SEGUNDOS = 30.0


CASOS_AMBIGUOS = [
    {
        "id": "int-006",
        "autor": "Ricardo Mena",
        "origen": "slack",
        "canal": "#feedback-programa",
        "idioma": "es",
        "texto": (
            "Sería genial tener más talleres prácticos sobre "
            "despliegue de modelos en la nube antes del hackathon."
        ),
        "dilema": (
            "¿Sentimiento neutral o positivo? "
            "¿Tema cloud_infraestructura o programa_hackathon?"
        ),
    },
    {
        "id": "int-011",
        "autor": "Gabriela Núñez",
        "origen": "discord",
        "canal": "#historias-egresados",
        "idioma": "es",
        "texto": (
            "El networking que generé en este programa me abrió "
            "puertas para colaborar en proyectos open source."
        ),
        "dilema": (
            "¿Tema comunidad o empleabilidad? "
            "¿Sentimiento positivo o muy_positivo?"
        ),
    },
    {
        "id": "int-016",
        "autor": "Isabel Quiroga",
        "origen": "formulario_web",
        "canal": "#formulario-testimonios",
        "idioma": "es",
        "texto": (
            "Nunca pensé que podría aprender SQL y Python al mismo "
            "tiempo, pero la metodología del curso lo hizo posible."
        ),
        "dilema": (
            "¿Sentimiento positivo o muy_positivo? "
            "¿Tema aprendizaje o programación?"
        ),
    },
    {
        "id": "int-020",
        "autor": "Lucía Paredes",
        "origen": "foro_alumnos",
        "canal": "categoria-programacion-basica",
        "idioma": "es",
        "texto": (
            "Sugiero agregar más ejercicios prácticos antes de pasar "
            "al módulo de estructuras de datos, se siente un salto grande."
        ),
        "dilema": (
            "¿Sentimiento negativo o neutral? "
            "¿Sugerencia feedback o comentario?"
        ),
    },
]


def _obtener_commit_actual() -> str | None:
    """Obtiene el commit actual únicamente para trazabilidad."""
    try:
        resultado = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return resultado.stdout.strip() or None


def _working_tree_tiene_cambios() -> bool | None:
    """Indica si la ejecución se hizo con cambios locales sin commit."""
    try:
        resultado = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=RAIZ,
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return bool(resultado.stdout.strip())


def construir_cadena(
    proveedor: str,
    modelo: str,
):
    """
    Construye una cadena directa para un proveedor y modelo concretos.

    No utiliza la política de fallback entre proveedores.
    """
    modelo_estructurado = obtener_modelo_analisis_estructurado(
        AnalisisMensaje,
        proveedor=proveedor,
        ruta="analisis",
        modelo=modelo,
    )

    return template_analisis | modelo_estructurado


def _evaluar(
    cadena,
    entrada: dict,
) -> dict:
    """Ejecuta una evaluación directa y devuelve salida serializable."""
    resultado = cadena.invoke(entrada)
    return resultado.model_dump()


def _es_respuesta_valida(resultado: dict | None) -> bool:
    """Distingue una respuesta semántica válida de un error registrado."""
    return (
        isinstance(resultado, dict)
        and "error" not in resultado
    )


def ejecutar_benchmark() -> None:
    # El override existe únicamente dentro de este proceso.
    # No modifica .env ni configuracion_ia.py.
    os.environ[
        "COMMUNITYLAB_NVIDIA_TIMEOUT_SEGUNDOS"
    ] = str(
        TIMEOUT_NVIDIA_BENCHMARK_SEGUNDOS
    )

    modelo_nvidia = obtener_modelo_nvidia_por_tier(
        TIER_ESTANDAR
    )
    modelo_gemini = MODELO_GEMINI

    print("=" * 80)
    print(
        "BENCHMARK EXPLORATORIO DE CALIBRACIÓN SEMÁNTICA"
    )
    print("=" * 80)
    print(f"NVIDIA NIM : {modelo_nvidia}")
    print(f"Gemini     : {modelo_gemini}")
    print(
        "Timeout NVIDIA benchmark:",
        f"{TIMEOUT_NVIDIA_BENCHMARK_SEGUNDOS:.0f} s",
    )
    print("Fallback   : desactivado para esta comparación")
    print("Ground truth humano: no")
    print("=" * 80)

    cadena_nvidia = construir_cadena(
        "nvidia_nim",
        modelo_nvidia,
    )
    cadena_gemini = construir_cadena(
        "gemini",
        modelo_gemini,
    )

    resultados = []

    for caso in CASOS_AMBIGUOS:
        # Entrada enviada al LLM.
        # tipo_original NO se utiliza como input ni ground truth.
        entrada_llm = {
            "origen": caso["origen"],
            "canal": caso["canal"],
            "idioma": caso["idioma"],
            "texto": caso["texto"],
        }

        registro = {
            "id": caso["id"],
            "autor": caso["autor"],
            "texto": caso["texto"],
            "dilema": caso["dilema"],
            "evaluacion_nvidia": None,
            "evaluacion_gemini": None,
        }

        print()
        print(
            f"[{caso['id']}] "
            f"{caso['texto']}"
        )

        # Ambos proveedores se evalúan de manera independiente.
        # El error de uno no activa al otro como fallback.
        try:
            registro["evaluacion_nvidia"] = _evaluar(
                cadena_nvidia,
                entrada_llm,
            )

            print(
                "  NVIDIA:",
                registro["evaluacion_nvidia"],
            )

        except Exception as error:
            registro["evaluacion_nvidia"] = {
                "error": type(error).__name__,
            }

            print(
                "  NVIDIA: ERROR",
                type(error).__name__,
            )

        try:
            registro["evaluacion_gemini"] = _evaluar(
                cadena_gemini,
                entrada_llm,
            )

            print(
                "  Gemini:",
                registro["evaluacion_gemini"],
            )

        except Exception as error:
            registro["evaluacion_gemini"] = {
                "error": type(error).__name__,
            }

            print(
                "  Gemini: ERROR",
                type(error).__name__,
            )

        resultados.append(registro)

    # Protección básica de integridad de la evidencia.
    ids_esperados = [
        caso["id"]
        for caso in CASOS_AMBIGUOS
    ]

    ids_obtenidos = [
        resultado.get("id")
        for resultado in resultados
    ]

    if ids_obtenidos != ids_esperados:
        raise RuntimeError(
            "La evidencia perdió IDs durante la ejecución. "
            f"Esperados={ids_esperados}; "
            f"obtenidos={ids_obtenidos}"
        )

    total_casos = len(resultados)

    respuestas_validas_nvidia = sum(
        _es_respuesta_valida(
            resultado["evaluacion_nvidia"]
        )
        for resultado in resultados
    )

    respuestas_validas_gemini = sum(
        _es_respuesta_valida(
            resultado["evaluacion_gemini"]
        )
        for resultado in resultados
    )

    comparaciones_completas = sum(
        _es_respuesta_valida(
            resultado["evaluacion_nvidia"]
        )
        and _es_respuesta_valida(
            resultado["evaluacion_gemini"]
        )
        for resultado in resultados
    )

    evidencia = {
        "tipo_evaluacion": (
            "exploratoria_cualitativa_casos_ambiguos"
        ),
        "objetivo": (
            "Observar estabilidad y diferencias semánticas "
            "entre proveedores bajo los mismos casos ambiguos."
        ),
        "es_ground_truth_humano": False,
        "permite_concluir_superioridad_proveedor": False,
        "sin_fallback": True,
        "tipo_original_enviado_al_llm": False,
        "ruta_analisis": "analisis",
        "tier_nvidia": TIER_ESTANDAR,
        "configuracion_experimental": {
            "timeout_nvidia_benchmark_segundos": (
                TIMEOUT_NVIDIA_BENCHMARK_SEGUNDOS
            ),
            "timeout_productivo_modificado": False,
        },
        "proveedores": {
            "nvidia_nim": {
                "modelo_ejecutado": modelo_nvidia,
            },
            "gemini": {
                "modelo_ejecutado": modelo_gemini,
            },
        },
        "trazabilidad_codigo": {
            "commit_head": _obtener_commit_actual(),
            "working_tree_con_cambios": (
                _working_tree_tiene_cambios()
            ),
        },
        "resumen_ejecucion": {
            "total_casos": total_casos,
            "respuestas_validas_nvidia": (
                respuestas_validas_nvidia
            ),
            "respuestas_validas_gemini": (
                respuestas_validas_gemini
            ),
            "comparaciones_completas": (
                comparaciones_completas
            ),
            "ejecucion_completa": (
                comparaciones_completas
                == total_casos
            ),
        },
        "resultados": resultados,
    }

    ruta_salida = (
        RAIZ
        / "docs"
        / "benchmark_calibracion_casos_ambiguos.json"
    )

    ruta_salida.write_text(
        json.dumps(
            evidencia,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("RESUMEN DE EJECUCIÓN")
    print("=" * 80)
    print(
        "Respuestas válidas NVIDIA:",
        f"{respuestas_validas_nvidia}/{total_casos}",
    )
    print(
        "Respuestas válidas Gemini:",
        f"{respuestas_validas_gemini}/{total_casos}",
    )
    print(
        "Comparaciones completas:",
        f"{comparaciones_completas}/{total_casos}",
    )
    print(
        "Ejecución completa:",
        comparaciones_completas == total_casos,
    )
    print()
    print(f"Evidencia guardada en: {ruta_salida}")
    print("=" * 80)


if __name__ == "__main__":
    ejecutar_benchmark()