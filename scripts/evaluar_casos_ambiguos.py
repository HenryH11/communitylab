from src.agentes.grafo import procesar_estados_por_lotes
from src.datos.ingesta import construir_estado_agente


mensajes = [
    {
        "id": "int-005",
        "texto": (
            "El servidor de Discord se siente muy activo, "
            "se nota el compromiso del equipo organizador."
        ),
        "esperado": "comentario",
    },
    {
        "id": "int-008",
        "texto": (
            "Buena onda el equipo de mentores, "
            "siempre responden rápido en el canal de dudas."
        ),
        "esperado": "comentario",
    },
    {
        "id": "int-009",
        "texto": (
            "Excelente iniciativa, ojalá sigan creciendo "
            "este tipo de comunidades en Latinoamérica."
        ),
        "esperado": "comentario",
    },
    {
        "id": "int-016",
        "texto": (
            "Nunca pensé que podría aprender SQL y Python al mismo tiempo, "
            "pero la metodología del curso lo hizo posible."
        ),
        "esperado": "testimonio",
    },
    {
        "id": "int-019",
        "texto": (
            "Buen material el de la última clase de funciones asíncronas, "
            "muy claro con los ejemplos."
        ),
        "esperado": "comentario",
    },
]


def principal():
    estados = []

    for mensaje in mensajes:
        interaccion = {
            "id": mensaje["id"],
            "autor": "evaluacion",
            "canal": "#casos-ambiguos",
            "tipo": mensaje["esperado"],
            "texto": mensaje["texto"],
        }
        estados.append(
            construir_estado_agente(
                interaccion,
                0,
                "casos_de_evaluacion",
            )
        )

    resultados = procesar_estados_por_lotes(
        estados,
        ids_contenido=set(),
    )
    aciertos = 0

    for mensaje, resultado in zip(mensajes, resultados):
        print("=" * 70)
        print("ID:", mensaje["id"])
        print("Esperado:", mensaje["esperado"])

        if resultado.get("errores"):
            print("Errores:", resultado["errores"])
            continue

        tipo_detectado = resultado["tipo_detectado"]
        print("Obtenido:", tipo_detectado)
        print("Sentimiento:", resultado["sentimiento"])
        print("Tema principal:", resultado["tema_principal"])

        if tipo_detectado == mensaje["esperado"]:
            print("Coincide")
            aciertos += 1
        else:
            print("Diferente")

    print()
    print(f"Resultado: {aciertos}/{len(mensajes)}")


if __name__ == "__main__":
    principal()