"""Adapta casos editoriales sin convertir sus etiquetas propuestas en resultados."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from .metadatos import PREFIJO_AUSENTE


def _metadato_o_marca(valor: object, campo: str) -> str:
    if valor is None:
        return PREFIJO_AUSENTE + campo
    if not isinstance(valor, str):
        raise ValueError(f"{campo} debe ser texto o estar ausente")
    return valor if valor.strip() else PREFIJO_AUSENTE + campo


def adaptar_casos_editoriales(documento: dict) -> dict:
    casos = documento.get("casos")
    if not isinstance(casos, list) or not casos:
        raise ValueError("Se esperaba una lista no vacia de casos")
    vistos = set()
    lotes = {}
    for caso in casos:
        if not isinstance(caso, dict):
            raise ValueError("Cada caso debe ser un objeto")
        identificador = caso.get("id")
        if (
            not isinstance(identificador, str) or not identificador.strip()
            or identificador != identificador.strip() or identificador in vistos
        ):
            raise ValueError("Los casos requieren IDs unicos y sin espacios exteriores")
        vistos.add(identificador)
        origen = _metadato_o_marca(caso.get("origen"), "origen")
        mensaje = {
            "id": identificador,
            "autor": _metadato_o_marca(caso.get("autor"), "autor"),
            "canal": _metadato_o_marca(caso.get("canal"), "canal"),
            "tipo": caso.get("tipo"),
            "texto": caso.get("texto"),
            "fecha": caso.get("fecha"),
            "idioma": _metadato_o_marca(caso.get("idioma"), "idioma"),
        }
        lotes.setdefault(origen, []).append(mensaje)
    return {
        "metadata": {
            "estado": "preparacion_no_resultado_capa_2",
            "usar_para_resultados_oficiales": False,
            "version_fuente": documento.get("version"),
            "estado_editorial_fuente": documento.get("estado"),
            "nota": "Marcas tecnicas de ausencia; etiquetas propuestas no importadas",
        },
        "lotes": [
            {
                "origen_comunidad": origen,
                "periodo_referencia": PREFIJO_AUSENTE + "periodo",
                "interacciones": mensajes,
            }
            for origen, mensajes in lotes.items()
        ],
    }


def principal():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--fecha-referencia", required=True)
    argumentos = parser.parse_args()
    documento = json.loads(argumentos.entrada.read_text(encoding="utf-8-sig"))
    entrada = adaptar_casos_editoriales(documento)
    from .entrega_ia import preparar_paquete_ia

    paquete = preparar_paquete_ia(
        entrada, fecha_referencia=argumentos.fecha_referencia, tamano_ciclo=20,
    )
    argumentos.salida.mkdir(parents=True, exist_ok=False)
    resumen = {
        "estado": "preparado_pendiente_capa_2",
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "capa_2_ejecutada": False,
        "usar_para_resultados_oficiales": False,
        "total": len(paquete["estados"]),
        "ciclos": len(paquete["plan"]["ciclos"]),
        "pendientes": paquete["plan"]["pendientes"],
        "incluidas_analisis": paquete["informe"]["resumen_sentimiento"]["incluidas"],
        "nota": "La fecha de referencia puntua relevancia; no fecha los mensajes sin fecha.",
    }
    for nombre, datos in (
        ("entrada_adaptada.json", entrada), ("paquete_preparado.json", paquete),
        ("resumen.json", resumen),
    ):
        with (argumentos.salida / nombre).open("x", encoding="utf-8") as archivo:
            json.dump(datos, archivo, ensure_ascii=False, indent=4)
            archivo.write("\n")
    print(json.dumps(resumen, ensure_ascii=True, indent=4))


if __name__ == "__main__":
    principal()
