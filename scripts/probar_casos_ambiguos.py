from src.agents.chains import cadena_analisis


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


aciertos = 0

for mensaje in mensajes:

    resultado = cadena_analisis.invoke(
        {"texto": mensaje["texto"]}
    )

    print("=" * 70)
    print("ID:", mensaje["id"])
    print("Esperado:", mensaje["esperado"])
    print("Obtenido:", resultado.tipo_detectado)
    print("Sentimiento:", resultado.sentimiento)
    print("Tema:", resultado.tema)

    if resultado.tipo_detectado == mensaje["esperado"]:
        print("✅ CORRECTO")
        aciertos += 1
    else:
        print("❌ DIFERENTE")


print()
print(f"Resultado: {aciertos}/{len(mensajes)}")