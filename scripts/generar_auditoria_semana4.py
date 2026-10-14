"""Genera el paquete reproducible de auditoría de Semana 4.

Flujo:
dataset
→ preparación de Data
→ procesamiento de Data Science
→ observabilidad
→ paquete JSON de auditoría

Este script realiza llamadas reales a IA cuando se ejecuta normalmente.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]

if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))


from src.agentes.auditoria_semana4 import (
    capturar_configuracion_ia_auditoria,
    cargar_eventos_observabilidad,
    construir_paquete_auditoria,
    paquete_auditoria_a_json,
)
from src.agentes.observabilidad import configurar_logging
from src.agentes.procesamiento import procesar_paquete_entrega
from src.datos.entrega_ia import preparar_paquete_ia


DATASET_POR_DEFECTO = (
    RAIZ
    / "src"
    / "datos"
    / "mensajes_comunidad_simulados.json"
)

SALIDA_POR_DEFECTO = (
    RAIZ
    / "salida"
    / "auditoria_semana4"
    / "auditoria_semana4.json"
)


def _ejecutar_git(*argumentos: str) -> str:
    """Ejecuta una consulta Git de solo lectura."""

    resultado = subprocess.run(
        ["git", *argumentos],
        cwd=RAIZ,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    return resultado.stdout.strip()


def obtener_estado_git() -> dict:
    """Captura SHA, rama y limpieza del working tree."""

    commit_sha = _ejecutar_git(
        "rev-parse",
        "HEAD",
    )

    rama = _ejecutar_git(
        "branch",
        "--show-current",
    )

    estado_porcelain = _ejecutar_git(
        "status",
        "--porcelain",
    )

    return {
        "commit_sha": commit_sha,
        "rama": rama,
        "working_tree_limpio": not bool(
            estado_porcelain
        ),
    }


def cargar_dataset(ruta: Path) -> dict:
    """Carga el dataset JSON de entrada."""

    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe el dataset: {ruta}"
        )

    with ruta.open(
        "r",
        encoding="utf-8",
    ) as archivo:
        datos = json.load(archivo)

    if not isinstance(datos, dict):
        raise ValueError(
            "El dataset debe contener un objeto JSON."
        )

    return datos


def calcular_sha256(ruta: Path) -> str:
    """Calcula SHA-256 del dataset utilizado."""

    hash_sha256 = hashlib.sha256()

    with ruta.open("rb") as archivo:
        for bloque in iter(
            lambda: archivo.read(1024 * 1024),
            b"",
        ):
            hash_sha256.update(bloque)

    return hash_sha256.hexdigest()


def ruta_relativa(ruta: Path) -> str:
    """Devuelve ruta relativa al repositorio cuando sea posible."""

    try:
        return ruta.resolve().relative_to(
            RAIZ.resolve()
        ).as_posix()
    except ValueError:
        return str(ruta.resolve())


def construir_argumentos() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Ejecuta el lote compartido y genera "
            "evidencia reproducible para la auditoría "
            "de Semana 4."
        )
    )

    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_POR_DEFECTO,
        help=(
            "Dataset de entrada. Por defecto utiliza "
            "src/datos/mensajes_comunidad_simulados.json"
        ),
    )

    parser.add_argument(
        "--salida",
        type=Path,
        default=SALIDA_POR_DEFECTO,
        help=(
            "Archivo JSON de auditoría que se generará."
        ),
    )

    parser.add_argument(
        "--fecha-referencia",
        required=True,
        help=(
            "Fecha ISO 8601 con zona horaria utilizada "
            "por Data para relevancia."
        ),
    )

    parser.add_argument(
        "--tamano-ciclo",
        type=int,
        default=20,
        help="Tamaño máximo del ciclo preparado por Data.",
    )

    parser.add_argument(
        "--permitir-working-tree-sucio",
        action="store_true",
        help=(
            "Permite ejecutar aunque existan cambios "
            "sin commit. No usar para la evidencia final."
        ),
    )

    return parser


def main() -> None:
    argumentos = construir_argumentos().parse_args()

    dataset = argumentos.dataset.resolve()
    salida = argumentos.salida.resolve()

    estado_git = obtener_estado_git()

    if (
        not estado_git["working_tree_limpio"]
        and not argumentos.permitir_working_tree_sucio
    ):
        raise RuntimeError(
            "El working tree tiene cambios sin commit. "
            "La ejecución se detiene para evitar generar "
            "evidencia final no reproducible. "
            "Haz commit de los cambios o utiliza "
            "--permitir-working-tree-sucio únicamente "
            "para una prueba no final."
        )

    datos = cargar_dataset(dataset)

    configuracion_ia = (
        capturar_configuracion_ia_auditoria()
    )

    ruta_log = configurar_logging()

    if ruta_log is None:
        raise RuntimeError(
            "La observabilidad está desactivada. "
            "La auditoría requiere COMMUNITYLAB_LOGS activo."
        )

    paquete_ia = preparar_paquete_ia(
        datos,
        fecha_referencia=argumentos.fecha_referencia,
        tamano_ciclo=argumentos.tamano_ciclo,
    )

    salida_procesamiento = procesar_paquete_entrega(
        paquete_ia
    )

    id_ejecucion = salida_procesamiento.get(
        "id_ejecucion"
    )

    if (
        not isinstance(id_ejecucion, str)
        or not id_ejecucion
    ):
        raise RuntimeError(
            "El procesamiento no devolvió un id_ejecucion válido."
        )

    eventos = cargar_eventos_observabilidad(
        ruta_log,
        id_ejecucion=id_ejecucion,
    )

    metadatos_ejecucion = {
        **estado_git,
        "reproducible": estado_git[
            "working_tree_limpio"
        ],
        "dataset": ruta_relativa(dataset),
        "dataset_sha256": calcular_sha256(dataset),
        "fecha_referencia": argumentos.fecha_referencia,
        "fecha_ejecucion_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "ruta_log": ruta_relativa(
            Path(ruta_log)
        ),
    }

    auditoria = construir_paquete_auditoria(
        datos_fuente=datos,
        paquete_ia=paquete_ia,
        salida_procesamiento=salida_procesamiento,
        eventos_observabilidad=eventos,
        configuracion_ia=configuracion_ia,
        metadatos_ejecucion=metadatos_ejecucion,
    )

    inconsistencias = auditoria.get(
        "inconsistencias",
        [],
    )

    if inconsistencias:
        raise RuntimeError(
            "La ejecución terminó, pero el paquete de "
            "auditoría contiene inconsistencias. "
            "No se escribirá como evidencia final. "
            f"Cantidad: {len(inconsistencias)}"
        )

    salida.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    salida.write_text(
        paquete_auditoria_a_json(auditoria),
        encoding="utf-8",
    )

    resumen = auditoria["resumen"]

    print()
    print("Auditoría Semana 4 generada correctamente.")
    print(f"Archivo: {salida}")
    print(
        f"Commit: {estado_git['commit_sha']}"
    )
    print(
        f"Rama: {estado_git['rama']}"
    )
    print(
        "Working tree limpio: "
        f"{estado_git['working_tree_limpio']}"
    )
    print(
        "Interacciones de entrada: "
        f"{resumen['total_entrada']}"
    )
    print(
        "Excluidas por Data: "
        f"{resumen['total_excluidas_data']}"
    )
    print(
        "Resultados DS: "
        f"{resumen['total_resultados_ds']}"
    )
    print(
        "Activos generados: "
        f"{resumen['total_activos_generados']}"
    )
    print(
        "Fallbacks en análisis: "
        f"{resumen['fallbacks_analisis']}"
    )
    print(
        "Fallbacks en activos: "
        f"{resumen['fallbacks_activos']}"
    )


if __name__ == "__main__":
    main()