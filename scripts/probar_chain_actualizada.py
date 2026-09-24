from src.agents.chains import cadena_analisis


mensaje = {
    "origen": "Discord_Grupo_ONE_G10",
    "canal": "#logros-y-empleos",
    "idioma": "es",
    "tipo_original": "comentario",
    "texto": (
        "Después de varios meses estudiando conseguí mi primer trabajo "
        "como analista de datos. Los proyectos de la comunidad fueron "
        "clave durante mi entrevista."
    ),
}


resultado = cadena_analisis.invoke(mensaje)


print()
print("Sentimiento:", resultado.sentimiento)
print("Tema principal:", resultado.tema_principal)
print("Subtema:", resultado.subtema)
print("Tipo original:", mensaje["tipo_original"])
print("Tipo detectado:", resultado.tipo_detectado)