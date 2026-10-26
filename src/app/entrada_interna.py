"""Entrada actual de Datos sin depender de archivos de demostracion."""

from src.datos.casos_editoriales import adaptar_casos_editoriales


def normalizar_entrada(documento: object) -> dict:
    if not isinstance(documento, dict):
        raise ValueError("La entrada debe ser un objeto JSON")
    if "casos" in documento:
        return adaptar_casos_editoriales(documento)
    lotes = documento.get("lotes", [documento])
    if not isinstance(lotes, list) or not lotes:
        raise ValueError("Se requiere una lista de lotes no vacia")
    ids = set()
    for lote in lotes:
        if not isinstance(lote, dict) or not isinstance(lote.get("interacciones"), list):
            raise ValueError("Cada lote requiere una lista de interacciones")
        for mensaje in lote["interacciones"]:
            if not isinstance(mensaje, dict):
                raise ValueError("Cada interaccion debe ser un objeto")
            identificador = mensaje.get("id")
            if not isinstance(identificador, str) or not identificador.strip() or identificador in ids:
                raise ValueError("Las interacciones requieren IDs unicos no vacios")
            if not isinstance(mensaje.get("texto"), str) or not mensaje["texto"].strip():
                raise ValueError("Las interacciones requieren texto no vacio")
            ids.add(identificador)
    if not ids:
        raise ValueError("El archivo no contiene mensajes")
    return documento
