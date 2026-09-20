from src.agents.chains import cadena_analisis


mensajes = [
    {
        "caso": "Testimonio / logro",
        "texto": (
            "Después de meses estudiando conseguí mi primer trabajo "
            "como analista de datos. Estoy muy agradecido con la comunidad "
            "porque sus consejos me ayudaron muchísimo."
        ),
    },
    {
        "caso": "Pregunta técnica",
        "texto": (
            "No entiendo cómo funcionan los nodos condicionales en LangGraph. "
            "¿Alguien podría mostrarme un ejemplo de cómo crear un router?"
        ),
    },
    {
        "caso": "Feedback positivo",
        "texto": (
            "El curso de LangChain me pareció excelente. "
            "Los ejemplos fueron claros y me ayudaron bastante a entender "
            "cómo trabajar con modelos de lenguaje."
        ),
    },
    {
        "caso": "Feedback negativo / queja",
        "texto": (
            "La plataforma se cae constantemente y varias veces perdí "
            "mi progreso. Deberían mejorar la estabilidad porque dificulta "
            "mucho completar las actividades."
        ),
    },
    {
        "caso": "Comentario neutral",
        "texto": (
            "Hoy terminé el módulo de Python y mañana comenzaré "
            "el contenido relacionado con bases de datos."
        ),
    },
]


for numero, mensaje in enumerate(mensajes, start=1):

    print("=" * 70)
    print(f"CASO {numero}: {mensaje['caso']}")
    print("=" * 70)

    print("Mensaje:")
    print(mensaje["texto"])
    print()

    resultado = cadena_analisis.invoke(
        {
            "texto": mensaje["texto"]
        }
    )

    print("Resultado:")
    print("Sentimiento:", resultado.sentimiento)
    print("Tema:", resultado.tema)
    print("Tipo:", resultado.tipo_detectado)
    print()