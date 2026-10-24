\
"""Evalúa el holdout congelado comparando NVIDIA NIM y Gemini.

Uso:
    python -m scripts.evaluar_holdout_proveedores
    python -m scripts.evaluar_holdout_proveedores --modo-sentimiento 3-clases

Modos de evaluación:
- exacto (predeterminado): compara los cinco niveles de sentimiento.
- 3-clases: agrupa muy_positivo/positivo y muy_negativo/negativo.
- El agrupamiento solo afecta las métricas; conserva las predicciones originales.


Características:
- mismo prompt para ambos proveedores;
- no envía tipo_original al LLM;
- sin fallback entre proveedores;
- varias corridas;
- accuracy, moda y estabilidad;
- SHA-256 del fixture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time

from collections import Counter, defaultdict
from pathlib import Path

from src.agentes.configuracion_ia import (
    PROVEEDOR_GEMINI,
    PROVEEDOR_NVIDIA_NIM,
)
from src.agentes.modelo_ia import obtener_modelo_analisis_estructurado
from src.agentes.modelos import AnalisisLote
from src.agentes.prompts.analisis import template_analisis_lote
from src.agentes.huellas import calcular_sha256_lf

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE_POR_DEFECTO = (
    RAIZ / "tests" / "fixtures" / "holdout_final_analisis_semana3.json"
)
SALIDA_POR_DEFECTO = (
    RAIZ / "salida" / "experimentos" / "holdout_final_resultados"
)

DIMENSIONES = {
    "sentimiento": "sentimiento_esperado",
    "tema_principal": "tema_esperado",
    "tipo_detectado": "tipo_esperado",
}

SENTIMIENTOS_VALIDOS = frozenset({
    "muy_positivo",
    "positivo",
    "neutral",
    "negativo",
    "muy_negativo",
})

def normalizar_sentimiento(sentimiento: str, modo: str = "exacto") -> str:
    """Adapta el sentimiento para su comparación durante la evaluación."""

    if modo == "exacto":
        return sentimiento

    if modo == "3-clases":
        equivalencias = {
            "muy_positivo": "positivo",
            "positivo": "positivo",
            "neutral": "neutral",
            "negativo": "negativo",
            "muy_negativo": "negativo",
        }

        if sentimiento not in equivalencias:
            raise ValueError(f"Sentimiento no reconocido: {sentimiento}")

        return equivalencias[sentimiento]

    raise ValueError(f"Modo de sentimiento no reconocido: {modo}")


def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", type=Path, default=FIXTURE_POR_DEFECTO)
    parser.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    parser.add_argument("--corridas", type=int, default=3)
    parser.add_argument("--tamano-lote", type=int, default=10)
    parser.add_argument("--max-intentos", type=int, default=3)
    parser.add_argument("--pausa", type=float, default=3.0)
    parser.add_argument(
        "--modo-sentimiento",
        choices=("exacto", "3-clases"),
        default="exacto",
        help="Modo de evaluación del sentimiento: exacto o agrupado en 3 clases.",
    )
    return parser.parse_args()


def cargar_holdout(ruta: Path) -> tuple[list[dict], str]:
    contenido = ruta.read_bytes()
    huella = hashlib.sha256(contenido).hexdigest()
    datos = json.loads(contenido.decode("utf-8"))
    casos = datos["casos"]

    if not isinstance(casos, list) or not casos:
        raise ValueError(
            "El fixture debe contener una lista con al menos un caso."
        )

    campos_obligatorios = {
        "id",
        "texto",
        "origen",
        "canal",
        "idioma",
        "sentimiento_esperado",
        "tema_esperado",
        "tipo_esperado",
    }

    for numero, caso in enumerate(casos, start=1):
        if not isinstance(caso, dict):
            raise ValueError(
                f"El caso {numero} debe ser un objeto JSON."
            )

        faltantes = campos_obligatorios - caso.keys()

        if faltantes:
            raise ValueError(
                f"El caso {numero} no contiene los campos obligatorios: "
                f"{', '.join(sorted(faltantes))}"
            )

        if not isinstance(caso["id"], str) or not caso["id"].strip():
            raise ValueError(
                f"El caso {numero} tiene un ID inválido."
            )

    ids = [caso["id"] for caso in casos]
    if len(ids) != len(set(ids)):
        raise ValueError("El holdout contiene IDs duplicados.")

    return casos, huella


def construir_cadena(proveedor: str):
    modelo = obtener_modelo_analisis_estructurado(
        AnalisisLote,
        proveedor=proveedor,
    )
    return template_analisis_lote | modelo


def ejecutar_corrida(
    proveedor: str,
    numero_corrida: int,
    casos: list[dict],
    tamano_lote: int,
    max_intentos: int,
    pausa: float,
    huella: str,
    salida: Path,
    huella_lf: str | None = None,
) -> dict:
    cadena = construir_cadena(proveedor)
    resultados = {}
    retries = []
    tiempos = []

    print()
    print("=" * 80)
    print(f"{proveedor} - CORRIDA {numero_corrida}")
    print("=" * 80)

    for numero_lote, inicio in enumerate(
        range(0, len(casos), tamano_lote),
        start=1,
    ):
        lote = casos[inicio : inicio + tamano_lote]

        mensajes = [
            {
                "id": caso["id"],
                "origen": caso["origen"],
                "canal": caso["canal"],
                "idioma": caso["idioma"],
                "texto": caso["texto"],
            }
            for caso in lote
        ]

        completado = False

        for intento in range(1, max_intentos + 1):
            comienzo = time.perf_counter()

            try:
                respuesta = cadena.invoke(
                    {
                        "mensajes_json": json.dumps(
                            mensajes,
                            ensure_ascii=False,
                        )
                    }
                )

                duracion = time.perf_counter() - comienzo

                if not isinstance(respuesta, AnalisisLote):
                    respuesta = AnalisisLote.model_validate(respuesta)

                ids_esperados = {caso["id"] for caso in lote}
                ids_obtenidos = {r.id for r in respuesta.resultados}

                if ids_esperados != ids_obtenidos:
                    raise RuntimeError(
                        "Los IDs devueltos no coinciden con el lote."
                    )

                for resultado in respuesta.resultados:
                    resultados[resultado.id] = resultado.model_dump()

                tiempos.append(duracion)
                completado = True

                print(
                    f"  lote {inicio + 1:02d}-"
                    f"{min(inicio + tamano_lote, len(casos)):02d} "
                    f"OK ({duracion:.1f}s)"
                )
                break

            except Exception as error:
                duracion = time.perf_counter() - comienzo
                retries.append(
                    {
                        "lote": numero_lote,
                        "intento": intento,
                        "error": type(error).__name__,
                        "duracion_s": round(duracion, 3),
                    }
                )

                print(
                    f"    lote {numero_lote}, intento {intento}/{max_intentos}: "
                    f"{type(error).__name__}"
                )

                if intento < max_intentos:
                    time.sleep(pausa)

        if not completado:
            raise RuntimeError(
                f"{proveedor}: lote {numero_lote} agotó intentos."
            )

    salida.mkdir(parents=True, exist_ok=True)
    ruta = salida / f"{proveedor}_corrida_{numero_corrida}.json"
    ruta.write_text(
        json.dumps(
            {
                "proveedor": proveedor,
                "corrida": numero_corrida,
                "holdout_sha256": huella,
                "holdout_sha256_lf": huella_lf,
                "resultados": resultados,
                "retries_externos": retries,
                "tiempos_lote_s": tiempos,
            },
            ensure_ascii=False,
            indent=4,
        ),
        encoding="utf-8",
    )

    return {"resultados": resultados, "retries": retries, "tiempos": tiempos}



def evaluar_corrida(
    casos: list[dict],
    resultados: dict,
    modo_sentimiento: str = "exacto",
) -> dict:
    total = len(casos)
    acumulados = {
        campo: {
            "correctos": 0,
            "por_clase": defaultdict(
                lambda: {"correctos": 0, "total": 0}
            ),
        }
        for campo in DIMENSIONES
    }
    triples = 0

    for caso in casos:
        coincidencias = 0

        for campo_predicho, campo_esperado in DIMENSIONES.items():
            esperado = caso[campo_esperado]
            obtenido = resultados[caso["id"]][campo_predicho]

            if campo_predicho == "sentimiento":
                if esperado not in SENTIMIENTOS_VALIDOS:
                    raise ValueError(
                        f"Sentimiento esperado no reconocido: {esperado}"
                    )

                esperado = normalizar_sentimiento(
                    esperado, modo_sentimiento
                )

                try:
                    obtenido = normalizar_sentimiento(
                        obtenido, modo_sentimiento
                    )
                except ValueError:
                    if modo_sentimiento != "3-clases":
                        raise
                    obtenido = None

            acierto = esperado == obtenido
            acumulado = acumulados[campo_predicho]

            acumulado["correctos"] += acierto
            acumulado["por_clase"][esperado]["total"] += 1
            acumulado["por_clase"][esperado]["correctos"] += acierto

            coincidencias += acierto

        triples += coincidencias == len(DIMENSIONES)

    resumen = {
        campo: {
            "correctos": valores["correctos"],
            "total": total,
            "accuracy": valores["correctos"] / total,
            "por_clase": dict(valores["por_clase"]),
        }
        for campo, valores in acumulados.items()
    }

    resumen["triple_correcto"] = {
        "correctos": triples,
        "total": total,
        "accuracy": triples / total,
    }

    return resumen


def modo(valores: list[str]) -> str:
    return Counter(valores).most_common(1)[0][0]


def resultados_moda(
    casos: list[dict],
    corridas: list[dict],
    modo_sentimiento: str = "exacto",
) -> dict:
    salida = {}

    for caso in casos:
        identificador = caso["id"]
        salida[identificador] = {}

        for campo in DIMENSIONES:
            valores = [
                corrida["resultados"][identificador][campo]
                for corrida in corridas
            ]

            if campo == "sentimiento":
                valores = [
                    normalizar_sentimiento(valor, modo_sentimiento)
                    for valor in valores
                    if valor in SENTIMIENTOS_VALIDOS
                ]

            salida[identificador][campo] = (
                modo(valores) if valores else None
            )


    return salida

def estabilidad(
    casos: list[dict],
    corridas: list[dict],
    modo_sentimiento: str = "exacto",
) -> dict:
    salida = {}

    for campo in DIMENSIONES:
        estables = 0

        for caso in casos:
            valores = {
                corrida["resultados"][caso["id"]][campo]
                for corrida in corridas
            }

            if campo == "sentimiento":
                if not valores.issubset(SENTIMIENTOS_VALIDOS):
                    continue

                valores = {
                    normalizar_sentimiento(valor, modo_sentimiento)
                    for valor in valores
                }

            estables += len(valores) == 1


        salida[campo] = {
            "estables": estables,
            "total": len(casos),
            "porcentaje": estables / len(casos),
        }

    return salida


def main() -> None:
    args = parsear_argumentos()

    if args.corridas < 1:
        raise ValueError("--corridas debe ser >= 1.")
    if args.tamano_lote < 1:
        raise ValueError("--tamano-lote debe ser >= 1.")

    casos, huella = cargar_holdout(args.fixture)
    huella_lf = calcular_sha256_lf(args.fixture)

    print("=" * 80)
    print("HOLDOUT")
    print("=" * 80)
    print(f"Casos: {len(casos)}")
    print(f"SHA-256: {huella}")

    ejecuciones = {"nvidia": [], "gemini": []}

    for nombre, proveedor in (
        ("nvidia", PROVEEDOR_NVIDIA_NIM),
        ("gemini", PROVEEDOR_GEMINI),
    ):
        for numero in range(1, args.corridas + 1):
            ejecuciones[nombre].append(
                ejecutar_corrida(
                    proveedor,
                    numero,
                    casos,
                    args.tamano_lote,
                    args.max_intentos,
                    args.pausa,
                    huella,
                    args.salida,
                    huella_lf=huella_lf,
                )
            )

    resumen = {
        "holdout_sha256": huella,
        "holdout_sha256_lf": huella_lf,
        "casos": len(casos),
        "corridas_por_proveedor": args.corridas,
        "tamano_lote": args.tamano_lote,
        "modo_sentimiento": args.modo_sentimiento,
    }

    for nombre, corridas in ejecuciones.items():
        resumen[nombre] = {
            "metricas_por_corrida": [
                evaluar_corrida(
                    casos,
                    corrida["resultados"],
                    args.modo_sentimiento,
                )
                for corrida in corridas
            ],
            "metricas_moda": evaluar_corrida(
                casos,
                resultados_moda(
                    casos,
                    corridas,
                    args.modo_sentimiento,
                ),
                args.modo_sentimiento,
            ),
            "estabilidad": estabilidad(
                casos,
                corridas,
                args.modo_sentimiento,
            ),
            "retries_externos": sum(
                len(corrida["retries"]) for corrida in corridas
            ),
            "tiempo_total_lotes_s": round(
                sum(
                    tiempo
                    for corrida in corridas
                    for tiempo in corrida["tiempos"]
                ),
                3,
            ),

        }

    args.salida.mkdir(parents=True, exist_ok=True)
    ruta_resumen = args.salida / "resumen_holdout_final.json"
    ruta_resumen.write_text(
        json.dumps(resumen, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )

    print()
    print("=" * 80)
    print("RESULTADO HOLDOUT")
    print("=" * 80)

    for nombre in ("nvidia", "gemini"):
        print()
        print(nombre.upper())
        metricas = resumen[nombre]["metricas_moda"]

        for campo in (*DIMENSIONES, "triple_correcto"):
            metrica = metricas[campo]
            print(
                f"  {campo}: {metrica['correctos']}/{metrica['total']} "
                f"({metrica['accuracy'] * 100:.1f}%)"
            )

        print("  Estabilidad:")
        for campo, metrica in resumen[nombre]["estabilidad"].items():
            print(
                f"    {campo}: {metrica['estables']}/{metrica['total']} "
                f"({metrica['porcentaje'] * 100:.1f}%)"
            )

        print(
            f"  Retries externos: {resumen[nombre]['retries_externos']}"
        )
        print(
            "  Tiempo acumulado de lotes: "
            f"{resumen[nombre]['tiempo_total_lotes_s']:.1f}s"
        )

    print()
    print(f"Resumen guardado en: {ruta_resumen}")


if __name__ == "__main__":
    main()
