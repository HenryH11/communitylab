"""Procesa las acciones del componente visual antes de dibujar la respuesta."""
from src.app.local import cargar_entrada, ejemplo, simular_plantilla

FORMATOS = {
    "instagram": "Post para LinkedIn",
    "linkedin": "Post para LinkedIn",
    "x": "Publicación corta",
    "sentimiento": "Resumen de comunidad",
    "temas": "Temas y tendencias",
    "preguntas": "Preguntas frecuentes",
}


def estado_inicial():
    return {"datos": [], "origen": "", "resultado": None, "aviso": None, "ultimo_evento": None, "exportacion": None}


def aplicar_evento(estado, evento):
    if not isinstance(evento, dict):
        return estado
    identidad = evento.get("id")
    if not isinstance(identidad, str) or not identidad or len(identidad) > 100 or identidad == estado["ultimo_evento"]:
        return estado
    nuevo = {**estado, "ultimo_evento": identidad, "aviso": None}
    try:
        accion = evento.get("accion")
        if not isinstance(accion, str):
            raise ValueError("Acción local no disponible.")
        if accion in {"cargar", "ejemplo"}:
            contenido = ejemplo() if accion == "ejemplo" else evento.get("contenido")
            if not isinstance(contenido, (str, bytes)):
                raise ValueError("Selecciona un archivo JSON válido.")
            mensajes = cargar_entrada(contenido)
            origen = "Ejemplo del proyecto · datos simulados" if accion == "ejemplo" else evento.get("nombre", "JSON pegado")
            if not isinstance(origen, str) or len(origen) > 250:
                raise ValueError("El nombre del archivo no es válido.")
            nuevo.update(datos=mensajes, origen=origen, resultado=None, exportacion=None,
                         aviso={"tipo": "exito", "texto": f"Lote validado: {len(mensajes)} mensajes. IA y OCI pendientes de integración."})
        elif accion == "simular":
            formato = evento.get("formato")
            if not isinstance(formato, str) or formato not in FORMATOS:
                raise ValueError("Selecciona una plantilla disponible.")
            resultado = simular_plantilla(estado["datos"], FORMATOS[formato])
            if formato in {"instagram", "linkedin", "x"}:
                nombres = {"instagram": "Post para Instagram", "linkedin": "Publicación para LinkedIn", "x": "Publicación para X"}
                resultado["plantilla"] = nombres[formato]
                for indice, borrador in enumerate(resultado["borradores"]):
                    borrador["titulo"] = f"{nombres[formato]} · borrador {indice + 1}"
                    if formato == "instagram":
                        borrador["contenido"] += "\n\nComparte tu experiencia en los comentarios.\n#Comunidad #Aprendizaje"
                    elif formato == "x":
                        fuente = next(m for m in estado["datos"] if m["id"] == borrador["fuentes"][0])
                        texto = fuente["texto"]
                        borrador["contenido"] = "Extracto de la comunidad (revisar contexto):\n" + texto[:200] + ("…" if len(texto) > 200 else "")
            nuevo["resultado"] = {**resultado, "formato": formato}
            nuevo["exportacion"] = None
            nuevo["aviso"] = {"tipo": "exito", "texto": "Borrador simulado localmente. No generado por IA ni guardado en OCI."}
        elif accion == "descargar":
            resultado = estado["resultado"]
            indices = evento.get("indices")
            if not resultado or not isinstance(indices, list) or not indices:
                raise ValueError("Selecciona al menos un borrador disponible.")
            if any(type(i) is not int or i < 0 or i >= len(resultado["borradores"]) for i in indices) or len(indices) != len(set(indices)):
                raise ValueError("La selección de borradores no es válida.")
            nuevo["exportacion"] = {"id": identidad, "nombre": "communitylab_borradores_simulados.json",
                "contenido": {**resultado, "borradores": [resultado["borradores"][i] for i in indices]}}
            nuevo["aviso"] = {"tipo": "exito", "texto": "Descarga local preparada con los borradores seleccionados. No se guardó en OCI."}
        elif accion == "descargar_datos":
            if not estado["datos"]:
                raise ValueError("Carga un lote válido antes de descargarlo.")
            nuevo["exportacion"] = {"id": identidad, "nombre": "communitylab_mensajes_validados.json",
                "contenido": {"modo": "validacion_local", "mensajes": estado["datos"]}}
            nuevo["aviso"] = {"tipo": "exito", "texto": "Descarga del lote validado preparada en este equipo."}
        elif accion == "vaciar":
            nuevo.update(datos=[], origen="", resultado=None, exportacion=None,
                         aviso={"tipo": "info", "texto": "Sesión vaciada. Los archivos de tu equipo se conservan."})
        else:
            raise ValueError("Acción local no disponible.")
    except (ValueError, UnicodeError, RecursionError) as error:
        nuevo["aviso"] = {"tipo": "error", "texto": str(error)}
    return nuevo
