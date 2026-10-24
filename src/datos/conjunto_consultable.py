"""Conjunto Consultable (Semana 5.1, subfase A): índice limpio de las salidas del MVP.

Aplana la entrega de DS en un registro por interacción con los campos estrictos que
consumen las herramientas del agente: id, canal, sentimiento, tema, tipo,
contenido_corto y fecha. Acepta el contrato de salida de DS (v1.3 y v1.4, campos
planos) y el paquete de auditoría (v1.2, con entrada/analisis/datos). La fecha no viaja
en el contrato: se toma del dataset de entrada, unido por id. Los mensajes que DS marca
como spam (v1.4) quedan fuera del índice y solo se cuentan. Sin IA ni red.
"""

import argparse
import json
from pathlib import Path

CAMPOS = ("id", "canal", "sentimiento", "tema", "tipo", "contenido_corto", "fecha")
VERSION = "1.1"
LARGO_CONTENIDO_CORTO = 160


def recortar(texto, largo=LARGO_CONTENIDO_CORTO):
    """Una sola línea de hasta `largo` caracteres, cortada en un espacio y con «…»."""
    plano = " ".join(str(texto or "").split())
    if len(plano) <= largo:
        return plano
    corte = plano[:largo - 1]
    if " " in corte:
        corte = corte[:corte.rindex(" ")]
    return corte.rstrip(" ,;:.") + "…"


def _mensajes_por_id(mensajes):
    """Indexa el dataset de entrada (lotes[].interacciones[] o una lista) por id."""
    if not mensajes:
        return {}
    lotes = mensajes.get("lotes", [mensajes]) if isinstance(mensajes, dict) else [{"interacciones": mensajes}]
    return {m["id"]: m for lote in lotes for m in lote.get("interacciones", []) if "id" in m}


def _plano(interaccion):
    """Normaliza una interacción v1.3/v1.4 (plana) o v1.2 (anidada). None si Datos la excluyó."""
    if "entrada" in interaccion or "analisis" in interaccion:
        if (interaccion.get("datos") or {}).get("excluido_por_data"):
            return None
        entrada, analisis = interaccion.get("entrada") or {}, interaccion.get("analisis") or {}
        return {"id": interaccion["id"], **entrada, **analisis}
    return interaccion


def construir_conjunto_consultable(entrega, mensajes=None):
    """Devuelve {version, campos, total, total_spam_excluido, registros} ordenado por id.

    Rechaza IDs repetidos.
    """
    originales = _mensajes_por_id(mensajes)
    registros, spam = {}, set()
    for interaccion in entrega.get("interacciones", []):
        fila = _plano(interaccion)
        if fila is None:
            continue
        identificador = fila["id"]
        if identificador in registros or identificador in spam:
            raise ValueError(f"ID duplicado en la entrega: {identificador}")
        if fila.get("es_spam_detectado") is True:
            # Igual que el resumen de DS, que lo deja fuera de la distribución de sentimientos.
            spam.add(identificador)
            continue
        original = originales.get(identificador, {})
        registros[identificador] = {
            "id": identificador,
            "canal": fila.get("canal") or original.get("canal"),
            "sentimiento": fila.get("sentimiento"),
            "tema": fila.get("tema_principal"),
            "tipo": fila.get("tipo_detectado"),
            "contenido_corto": recortar(fila.get("texto") or original.get("texto")),
            "fecha": fila.get("fecha") or original.get("fecha"),
        }
    filas = [registros[i] for i in sorted(registros)]
    return {"version": VERSION, "campos": list(CAMPOS), "total": len(filas),
            "total_spam_excluido": len(spam), "registros": filas}


def principal(argumentos=None):
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    parser.add_argument("--entrega", required=True, help="JSON de DS (contrato v1.3/v1.4 o paquete de auditoría v1.2)")
    parser.add_argument("--mensajes", help="dataset de entrada, para tomar la fecha por id")
    parser.add_argument("--salida", required=True)
    args = parser.parse_args(argumentos)
    leer = lambda ruta: json.loads(Path(ruta).read_text(encoding="utf-8"))
    conjunto = construir_conjunto_consultable(leer(args.entrega), leer(args.mensajes) if args.mensajes else None)
    # Bytes con saltos LF: en Windows, write_text escribiría CRLF en el archivo que CE sube al bucket.
    Path(args.salida).write_bytes((json.dumps(conjunto, ensure_ascii=False, indent=4) + "\n").encode("utf-8"))
    sin_fecha = sum(1 for r in conjunto["registros"] if not r["fecha"])
    print(json.dumps({"registros": conjunto["total"], "sin_fecha": sin_fecha,
                      "spam_excluido": conjunto["total_spam_excluido"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
