from src.agents.nodes.analyzer_node import analizar_mensaje
from src.agents.state import AgentState


estado: AgentState = {
    "id": "int-prueba-001",
    "autor": "Arnold",
    "canal": "#logros-y-empleos",
    "origen": "Discord",
    "idioma": "es",
    "texto": (
        "Después de meses estudiando conseguí mi primer trabajo "
        "como analista de datos gracias a los proyectos que desarrollé."
    ),
    "tipo_original": "comentario",
    "score_relevancia": 90,
    "rutas": [],
    "activos_generados": {},
    "errores": [],
}


resultado_nodo = analizar_mensaje(estado)


print("Estado de entrada:")
print(estado)

print()
print("Resultado del nodo:")
print(resultado_nodo)

print()

estado_actualizado = {
    **estado,
    **resultado_nodo,
}

print("Estado después del análisis:")
print(estado_actualizado)