"""Ejecutor de una sola pasada; invocar mediante el programador de Cloud."""

import logging
from pathlib import Path

from dotenv import load_dotenv

from src.app.plantillas_diarias import RepositorioCatalogo, actualizar_catalogo


def principal() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    logging.basicConfig(level=logging.INFO)
    try:
        catalogo = actualizar_catalogo(RepositorioCatalogo.desde_entorno())
    except Exception:
        logging.exception("No se pudo confirmar la actualización del catálogo diario")
        return 1
    if catalogo is None:
        logging.info("Todavía no son las 13:00 UTC; no se genera contenido")
        return 0
    logging.info(
        "Catálogo confirmado en OCI: %s entradas, %s pendientes",
        len(catalogo.entradas), len(catalogo.fallos),
    )
    return 2 if catalogo.fallos else 0


if __name__ == "__main__":
    raise SystemExit(principal())
