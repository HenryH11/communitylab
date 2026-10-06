"""Funciones compartidas para preparar datos e informes de demostración."""

import json
from datetime import datetime, timezone
from pathlib import Path

from src.datos.entrega_ia import preparar_paquete_ia
from src.datos.relevancia import ConfiguracionRelevancia, leer_fecha


RAIZ_REPOSITORIO = Path(__file__).resolve().parents[1]
RUTA_CONJUNTO_DATOS = RAIZ_REPOSITORIO / "src/datos/mensajes_comunidad_simulados.json"


def obtener_lotes(conjunto_datos: dict) -> list[dict]:
    if "lotes" in conjunto_datos:
        return conjunto_datos["lotes"]
    if "interacciones" in conjunto_datos:
        return [conjunto_datos]
    raise ValueError("Los datos no contienen 'lotes' ni 'interacciones'")


def obtener_fecha_referencia(lotes: list[dict]) -> datetime:
    fechas_validas = []

    for lote in lotes:
        for mensaje in lote.get("interacciones", []):
            fecha = mensaje.get("fecha")
            if not fecha:
                continue

            try:
                fechas_validas.append(leer_fecha(fecha))
            except ValueError:
                continue

    if fechas_validas:
        return max(fechas_validas)
    return datetime.now(timezone.utc)


def cargar_paquete_demostracion(tamano_ciclo: int = 12) -> dict:
    """Carga el conjunto de ejemplo mediante la API pública de Datos."""
    with RUTA_CONJUNTO_DATOS.open("r", encoding="utf-8") as archivo:
        conjunto_datos = json.load(archivo)

    paquete = preparar_paquete_ia(
        conjunto_datos,
        fecha_referencia=obtener_fecha_referencia(
            obtener_lotes(conjunto_datos)
        ),
        configuracion=ConfiguracionRelevancia(),
        tamano_ciclo=tamano_ciclo,
    )
    return paquete


def obtener_evaluaciones_por_id(informe: dict) -> dict[str, dict]:
    evaluaciones = {}

    for lote in informe["lotes"]:
        for evaluacion in lote["evaluaciones"]:
            mensaje_id = evaluacion.get("id")
            if mensaje_id is None:
                continue
            if mensaje_id in evaluaciones:
                raise ValueError(f"ID repetido en el informe: {mensaje_id}")
            evaluaciones[mensaje_id] = evaluacion

    return evaluaciones
