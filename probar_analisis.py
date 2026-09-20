from src.agents.chains import cadena_analisis


mensaje = """
Después de meses estudiando conseguí mi primer trabajo
como analista de datos. Estoy muy agradecido con la
comunidad porque sus consejos me ayudaron muchísimo.
"""


resultado = cadena_analisis.invoke(
    {
        "texto": mensaje
    }
)


print(resultado)
print()
print("Sentimiento:", resultado.sentimiento)
print("Tema:", resultado.tema)
print("Tipo:", resultado.tipo_detectado)