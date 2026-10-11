"""Reprocesa los fallos reintentables de una entrega DS guardada."""

import argparse
import json
from pathlib import Path

from src.agentes.entrega_resultados import (
    entrega_resultados_a_json,
    preparar_entrega_resultados,
)
from src.agentes.recuperacion import reprocesar_fallidos


RAIZ = Path(__file__).resolve().parents[1]
RUTA_ENTRADA = RAIZ / "output" / "entrega_ciencia_datos_completa.json"
RUTA_SALIDA = RAIZ / "output" / "entrega_ciencia_datos_reprocesada.json"


def principal(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, default=RUTA_ENTRADA)
    parser.add_argument("--salida", type=Path, default=RUTA_SALIDA)
    parser.add_argument(
        "--incluir-permanentes",
        action="store_true",
        help="Reintenta también fallos no transitorios (validación, configuración).",
    )
    argumentos = parser.parse_args(argv)

    entrega = json.loads(argumentos.entrada.read_text(encoding="utf-8"))
    interacciones = entrega["interacciones"]
    objetivo = [
        interaccion["id"]
        for interaccion in interacciones
        if any(
            argumentos.incluir_permanentes or fallo.get("reintentable") is True
            for fallo in interaccion.get("fallos", [])
        )
    ]
    if not objetivo:
        print("No hay fallos para reprocesar.")
        return 0

    print(f"Reprocesando {len(objetivo)} interacciones: {', '.join(objetivo)}")
    salida = reprocesar_fallidos(
        {
            "resultados": interacciones,
            "pendientes": entrega.get("pendientes", []),
            "ids_pendientes": entrega.get("ids_pendientes", []),
            "id_ejecucion": entrega.get("id_ejecucion"),
        },
        solo_reintentables=not argumentos.incluir_permanentes,
    )
    nueva = preparar_entrega_resultados(salida)

    argumentos.salida.parent.mkdir(parents=True, exist_ok=True)
    argumentos.salida.write_text(
        entrega_resultados_a_json(nueva),
        encoding="utf-8",
    )

    resumen = nueva["resumen_comunidad"]
    print(f"Fallos restantes: {resumen['total_fallos']}")
    print(f"Fallos reintentables restantes: {resumen['total_fallos_reintentables']}")
    print(f"Entrega guardada en: {argumentos.salida}")
    return 1 if nueva["ids_reintentables"] else 0


if __name__ == "__main__":
    raise SystemExit(principal())
