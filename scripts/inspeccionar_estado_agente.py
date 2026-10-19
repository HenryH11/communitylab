from src.datos.ingesta import construir_estado_agente
from src.agentes.estado_agente import EstadoAgente


def principal():
    mensaje = {
        "id": "int-prueba-001",
        "autor": "Arnold",
        "canal": "#logros-y-empleos",
        "tipo": "comentario",
        "texto": "Conseguí mi primer trabajo como analista de datos.",
    }
    estado: EstadoAgente = construir_estado_agente(
        mensaje,
        90,
        "Discord",
    )
    print(estado)


if __name__ == "__main__":
    principal()