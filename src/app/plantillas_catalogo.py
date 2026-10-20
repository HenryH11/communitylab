"""Catálogo de la página de Plantillas (boceto de Jhonattan, Semana 5.1).

Cada plantilla muestra lo que el pipeline ya generó; ninguna vuelve a llamar a
la IA. Las de tipo "activo" leen `activos_generados[tipo]` y pasan por la
curaduría; las de tipo "analisis" resumen campos del análisis; las de tipo
"proxima" esperan a que el equipo defina su generador.
"""

from collections import Counter

CATEGORIAS = ("Todas las plantillas", "Contenido para redes", "Analíticas", "Preguntas frecuentes")

PLANTILLAS = (
    {
        "id": "linkedin", "nombre": "Publicación para LinkedIn", "icono": "in",
        "categoria": "Contenido para redes", "etiqueta": "CONTENIDO",
        "descripcion": "Post profesional con hallazgos", "detalle": "Tono profesional + CTA",
        "fuente": "activo", "tipo": "linkedin",
        "red": ("LinkedIn", "https://www.linkedin.com/feed/"),
        "objetivo": "Informar y generar interés", "tono": "Profesional y cercano",
    },
    {
        "id": "boletin", "nombre": "Destacado para newsletter", "icono": "✉",
        "categoria": "Contenido para redes", "etiqueta": "CONTENIDO",
        "descripcion": "Sección, titular y resumen", "detalle": "Bloque listo para el boletín",
        "fuente": "activo", "tipo": "boletin",
        "objetivo": "Mantener informada a la comunidad", "tono": "Claro y cercano",
    },
    {
        "id": "caso_exito", "nombre": "Caso de éxito", "icono": "★",
        "categoria": "Contenido para redes", "etiqueta": "CONTENIDO",
        "descripcion": "Historia real de la comunidad", "detalle": "Titular + resumen",
        "fuente": "activo", "tipo": "caso_exito",
        "objetivo": "Mostrar logros de la comunidad", "tono": "Inspirador",
    },
    {
        "id": "instagram", "nombre": "Post para Instagram", "icono": "IG",
        "categoria": "Contenido para redes", "etiqueta": "CONTENIDO",
        "descripcion": "Caption, CTA y hashtags", "detalle": "Formato corto + hashtags",
        "fuente": "proxima",
    },
    {
        "id": "x", "nombre": "Publicación para X", "icono": "X",
        "categoria": "Contenido para redes", "etiqueta": "CONTENIDO",
        "descripcion": "Idea breve o hilo estructurado", "detalle": "Post o secuencia",
        "fuente": "proxima",
    },
    {
        "id": "sentimiento", "nombre": "Sentimiento de comunidad", "icono": "%",
        "categoria": "Analíticas", "etiqueta": "ANALÍTICA",
        "descripcion": "Distribución y explicación", "detalle": "Gráfico + resumen",
        "fuente": "analisis", "campo": "sentimiento",
    },
    {
        "id": "temas", "nombre": "Temas y tendencias", "icono": "#",
        "categoria": "Analíticas", "etiqueta": "ANALÍTICA",
        "descripcion": "Asuntos, frecuencias, señales", "detalle": "Ranking + hallazgos",
        "fuente": "analisis", "campo": "tema_principal",
    },
    {
        "id": "insight_mejora", "nombre": "Oportunidades de mejora", "icono": "↗",
        "categoria": "Analíticas", "etiqueta": "ANALÍTICA",
        "descripcion": "Hallazgos y sugerencias detectadas", "detalle": "Hallazgo + área",
        "fuente": "activo", "tipo": "insight_mejora",
        "objetivo": "Priorizar mejoras con el equipo", "tono": "Objetivo",
    },
    {
        "id": "preguntas_frecuentes", "nombre": "Preguntas de la comunidad", "icono": "Q",
        "categoria": "Preguntas frecuentes", "etiqueta": "CONOCIMIENTO",
        "descripcion": "Preguntas recurrentes detectadas", "detalle": "FAQ derivadas de datos",
        "fuente": "activo", "tipo": "preguntas_frecuentes",
        "objetivo": "Resolver dudas frecuentes", "tono": "Claro y didáctico",
    },
)

TIPOS_EN_CATALOGO = {p["tipo"] for p in PLANTILLAS if p["fuente"] == "activo"}


def filtrar(busqueda="", categoria=CATEGORIAS[0], plantillas=PLANTILLAS):
    """Plantillas que coinciden con la categoría y con el texto buscado."""
    texto = " ".join(str(busqueda or "").lower().split())
    return [
        p for p in plantillas
        if (categoria == CATEGORIAS[0] or p["categoria"] == categoria)
        and (not texto or texto in f"{p['nombre']} {p['descripcion']} {p['detalle']}".lower())
    ]


def borradores(plantilla, resultados):
    """(id, mensaje, activo) de cada activo generado para una plantilla de tipo activo."""
    if plantilla.get("fuente") != "activo":
        return []
    return [
        (id_msg, data, data["activos_generados"][plantilla["tipo"]])
        for id_msg, data in resultados.items()
        if plantilla["tipo"] in (data.get("activos_generados") or {})
    ]


def distribucion(plantilla, resultados):
    """Conteo del campo de análisis de una plantilla analítica, de mayor a menor."""
    if plantilla.get("fuente") != "analisis":
        return []
    return Counter(
        data.get(plantilla["campo"]) or "sin dato" for data in resultados.values()
    ).most_common()


def contar(plantilla, resultados):
    """Número que muestra la tarjeta: borradores o mensajes analizados."""
    if plantilla.get("fuente") == "activo":
        return len(borradores(plantilla, resultados))
    if plantilla.get("fuente") == "analisis":
        return len(resultados)
    return 0


def tipos_sin_plantilla(resultados):
    """Tipos de activo que el pipeline generó y que el catálogo aún no conoce."""
    return sorted({
        tipo for data in resultados.values()
        for tipo in (data.get("activos_generados") or {})
        if tipo not in TIPOS_EN_CATALOGO
    })
