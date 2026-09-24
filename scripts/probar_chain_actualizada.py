import time

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


print("=" * 60)
print("PRUEBA DE CHAIN ACTUALIZADA")
print("=" * 60)

print()
print("Mensaje a analizar:")
print(mensaje["texto"])

print()
print("Enviando mensaje a Gemini...")

inicio = time.perf_counter()

try:
    resultado = cadena_analisis.invoke(mensaje)

    fin = time.perf_counter()
    tiempo_total = fin - inicio

    print("Respuesta recibida correctamente.")
    print()

    print("RESULTADO")
    print("-" * 60)
    print("Sentimiento:", resultado.sentimiento)
    print("Tema principal:", resultado.tema_principal)
    print("Subtema:", resultado.subtema)
    print("Tipo original:", mensaje["tipo_original"])
    print("Tipo detectado:", resultado.tipo_detectado)

    print()
    print(f"Tiempo de respuesta: {tiempo_total:.2f} segundos")

except Exception as error:
    fin = time.perf_counter()
    tiempo_total = fin - inicio

    print()
    print("ERROR")
    print("-" * 60)
    print(f"Tipo de error: {type(error).__name__}")
    print(f"Detalle: {error}")
    print(f"Tiempo transcurrido antes del error: {tiempo_total:.2f} segundos")