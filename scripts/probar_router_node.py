from src.agents.nodes.router_node import determinar_rutas
from src.agents.state import AgentState


casos = [
    {
        "nombre": "Testimonio relevante",
        "state": {
            "tipo_detectado": "testimonio",
            "sentimiento": "muy_positivo",
            "score_relevancia": 90,
        },
    },
    {
        "nombre": "Pregunta técnica",
        "state": {
            "tipo_detectado": "pregunta_tecnica",
            "sentimiento": "neutral",
            "score_relevancia": 75,
        },
    },
    {
        "nombre": "Feedback",
        "state": {
            "tipo_detectado": "feedback",
            "sentimiento": "negativo",
            "score_relevancia": 80,
        },
    },
    {
        "nombre": "Comentario general",
        "state": {
            "tipo_detectado": "comentario",
            "sentimiento": "positivo",
            "score_relevancia": 70,
        },
    },
    {
        "nombre": "Testimonio con baja relevancia",
        "state": {
            "tipo_detectado": "testimonio",
            "sentimiento": "muy_positivo",
            "score_relevancia": 20,
        },
    },
]


for caso in casos:
    estado: AgentState = caso["state"]

    resultado = determinar_rutas(estado)

    print("=" * 60)
    print(caso["nombre"])
    print("Tipo:", estado.get("tipo_detectado"))
    print("Sentimiento:", estado.get("sentimiento"))
    print("Score:", estado.get("score_relevancia"))
    print("Rutas:", resultado["rutas"])