"""Compatibilidad de la carga interna; el escritor vive en services.ingest_server.

Conserva el import publico y el adaptador optativo de Functions. No instala FDK
ni ejecuta conexiones al importar.
"""

import importlib
import io
import json
import logging
from typing import Any

from src.services.ingest_server import (
    CAMPOS_CONJUNTO as CAMPOS_CONJUNTO,
    VERSION_CONJUNTO as VERSION_CONJUNTO,
    obtener_cliente_secretos as obtener_cliente_secretos,
    obtener_conexion as obtener_conexion,
    obtener_secreto_vault as obtener_secreto_vault,
    sincronizar_conjunto as sincronizar_conjunto,
    validar_registro as validar_registro,
)

LOGGER = logging.getLogger(__name__)


def handler(ctx: Any, data: io.BytesIO | None = None) -> Any:
    """Adaptador Functions opcional; requiere instalar FDK en ese ejecutor."""
    response = importlib.import_module("fdk.response")
    try:
        if data is None:
            raise ValueError("el cuerpo de la petición está vacío")
        documento = json.loads(data.getvalue().decode("utf-8"))
        resultado = sincronizar_conjunto(documento, instantanea_completa=True)
        return response.Response(
            ctx, response_data=json.dumps(resultado),
            headers={"Content-Type": "application/json"}, status_code=200,
        )
    except (ValueError, TypeError) as error:
        LOGGER.warning("Error de validación en ingesta: %s", error)
        return response.Response(
            ctx, response_data=json.dumps({"error": str(error)}),
            headers={"Content-Type": "application/json"}, status_code=400,
        )
    except Exception as error:
        LOGGER.error("Fallo crítico durante la ingesta (%s)", type(error).__name__)
        return response.Response(
            ctx, response_data=json.dumps({"error": "error interno al sincronizar la instantánea"}),
            headers={"Content-Type": "application/json"}, status_code=500,
        )
