"""Demostración local. El adaptador real de DA/DS queda pendiente y no se importa."""
from collections import Counter
import json
from pathlib import Path

from src.datos.ingesta import validar_y_limpiar

MAX_BYTES = 5 * 1024 * 1024
MAX_MENSAJES = 1000
PLANTILLAS = {
    "Post para LinkedIn": {"descripcion": "Una historia de la comunidad como borrador para redes.", "tipos": {"testimonio"}},
    "Publicación corta": {"descripcion": "Una idea breve basada en un testimonio.", "tipos": {"testimonio"}},
    "Preguntas frecuentes": {"descripcion": "Preguntas del lote con respuestas pendientes de revisión.", "tipos": {"pregunta_tecnica", "pregunta_programa"}},
    "Resumen de comunidad": {"descripcion": "Un resumen con conteos del archivo cargado.", "tipos": None},
    "Temas y tendencias": {"descripcion": "Agrupación por tipos y canales declarados.", "tipos": None},
    "Oportunidades de mejora": {"descripcion": "Comentarios de feedback para revisar con el equipo.", "tipos": {"feedback"}},
}


def ejemplo():
    return (Path(__file__).resolve().parents[1] / "datos" / "mensajes_comunidad_simulados.json").read_bytes()


def _rechazar_constante(valor):
    raise ValueError(f"JSON contiene un valor no permitido: {valor}")


def cargar_entrada(contenido):
    if isinstance(contenido, str):
        contenido = contenido.encode("utf-8")
    if len(contenido) > MAX_BYTES:
        raise ValueError("El archivo supera 5 MB.")
    try:
        datos = json.loads(contenido.decode("utf-8-sig"), parse_constant=_rechazar_constante)
    except json.JSONDecodeError as error:
        raise ValueError(f"JSON inválido: línea {error.lineno}, columna {error.colno}.") from error
    except UnicodeDecodeError as error:
        raise ValueError("El archivo debe estar codificado en UTF-8.") from error
    limpios = validar_y_limpiar(datos)
    lotes = limpios.get("lotes", [limpios])
    if not lotes or any(not lote["interacciones"] for lote in lotes):
        raise ValueError("Cada lote debe contener al menos una interacción.")
    total = sum(len(lote["interacciones"]) for lote in lotes)
    if total > MAX_MENSAJES:
        raise ValueError("El límite local es de 1.000 mensajes.")
    existentes = [m["id"] for lote in lotes for m in lote["interacciones"] if "id" in m]
    if len(existentes) != len(set(existentes)):
        raise ValueError("Hay identificadores id duplicados; usa un id único por mensaje.")
    usados = set(existentes)
    mensajes = []
    for lote in lotes:
        for mensaje in lote["interacciones"]:
            if not mensaje["texto"].strip():
                raise ValueError("Hay un mensaje vacío después de la limpieza.")
            if len(mensaje["texto"]) > 50000:
                raise ValueError("Un mensaje supera 50.000 caracteres.")
            identificador = mensaje.get("id")
            if identificador is None:
                numero = len(mensajes) + 1
                identificador = f"local-{numero:04d}"
                while identificador in usados:
                    numero += 1
                    identificador = f"local-{numero:04d}"
                usados.add(identificador)
            mensajes.append({**mensaje, "id": identificador,
                "origen_comunidad": lote["origen_comunidad"], "periodo_referencia": lote["periodo_referencia"]})
    return mensajes


def simular_plantilla(mensajes, plantilla):
    if not mensajes or plantilla not in PLANTILLAS:
        raise ValueError("Carga mensajes y elige una plantilla disponible.")
    tipos = PLANTILLAS[plantilla]["tipos"]
    candidatos = [m for m in mensajes if tipos is None or m["tipo"] in tipos]
    borradores = []
    if plantilla in {"Resumen de comunidad", "Temas y tendencias"}:
        conteos = Counter(m["tipo"] for m in mensajes)
        canales = Counter(m["canal"] for m in mensajes)
        contenido = f"El lote contiene {len(mensajes)} mensajes en {len(canales)} canales.\n\nTipos declarados:\n"
        contenido += "\n".join(f"• {tipo}: {cantidad}" for tipo, cantidad in conteos.most_common())
        contenido += "\n\nActividad por canal:\n" + "\n".join(f"• {canal}: {cantidad}" for canal, cantidad in canales.most_common())
        borradores.append({"titulo": plantilla, "contenido": contenido, "fuentes": [m["id"] for m in mensajes]})
    else:
        for mensaje in candidatos:
            texto = mensaje["texto"]
            if plantilla == "Preguntas frecuentes":
                contenido = f"Pregunta recibida:\n{texto}\n\nRespuesta: pendiente de revisión por el equipo. No se ha inventado una respuesta."
            elif plantilla == "Oportunidades de mejora":
                contenido = f"Feedback recibido:\n{texto}\n\nPróximo paso propuesto: revisar este comentario con el equipo y acordar una acción."
            else:
                contenido = f"Voces de nuestra comunidad\n\n«{texto}»\n\nAntes de publicar: verifica el contexto y solicita autorización al autor para utilizar su testimonio."
            borradores.append({"titulo": f"{plantilla} · {mensaje['autor']}", "contenido": contenido, "fuentes": [mensaje["id"]]})
    return {"modo": "simulado_local", "generado_por_ia": False, "guardado_en_nube": False,
        "plantilla": plantilla, "criterio": "Selección por tipo declarado; no valida elegibilidad para producción.",
        "borradores": borradores}
