"""Comprueba lectura de Oracle y Object Storage sin escribir ni mostrar secretos."""

import json
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

from src.config import db_client, oci_client


def principal() -> int:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    resultados = {}
    try:
        conjunto = db_client.leer_conjunto()
        resultados["oracle"] = {
            "estado": "accesible",
            "total": conjunto["total"],
            "version": conjunto["version"],
        }
    except Exception as error:
        resultados["oracle"] = {"estado": "error", "tipo": type(error).__name__}
        print(f"Oracle: lectura fallida ({type(error).__name__}).", file=sys.stderr)

    try:
        cliente, namespace = oci_client.obtener_cliente()
        bucket = os.getenv("OCI_BUCKET_NAME", oci_client.BUCKET_PREDETERMINADO)
        respuesta = cliente.list_objects(
            namespace_name=namespace,
            bucket_name=bucket,
            prefix="plantillas/",
            limit=5,
        )
        if respuesta is None:
            raise RuntimeError("OCI no devolvio el listado")
        resultados["bucket"] = {
            "estado": "accesible",
            "objetos_en_muestra": len(respuesta.data.objects),
            "hay_mas": bool(respuesta.data.next_start_with),
        }
    except Exception as error:
        resultados["bucket"] = {"estado": "error", "tipo": type(error).__name__}
        print(f"Bucket: lectura fallida ({type(error).__name__}).", file=sys.stderr)

    print(json.dumps(resultados, ensure_ascii=True, indent=4))
    return int(any(r["estado"] != "accesible" for r in resultados.values()))


if __name__ == "__main__":
    sys.exit(principal())
