from src.datos.ingesta import construir_estado_agente
from src.agentes.nodos.nodo_analizador import analizar_mensaje


def principal():
    mensaje = {
        "id": "int-prueba-001",
        "autor": "Arnold",
        "canal": "#logros-y-empleos",
        "tipo": "comentario",
        "texto": (
            "Después de meses estudiando conseguí mi primer trabajo "
            "como analista de datos gracias a los proyectos que desarrollé."
        ),
    }
    estado = construir_estado_agente(
        mensaje,
        90,
        "Discord",
    )
    resultado_nodo = analizar_mensaje(estado)

    print("Estado de entrada:")
    print(estado)

    estado_actualizado = {**estado, **resultado_nodo}
    print("\nEstado después del análisis:")
    print(estado_actualizado)

if __name__ == "__main__":
    principal()
