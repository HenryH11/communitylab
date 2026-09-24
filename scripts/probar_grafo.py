from src.agents.graph import grafo
from src.agents.state import AgentState


estado_inicial: AgentState = {
    "id": "int-prueba-001",
    "autor": "Arnold",
    "canal": "#logros-y-empleos",
    "origen": "Discord_Grupo_ONE_G10",
    "idioma": "es",
    "texto": (
        "Después de varios meses estudiando conseguí mi primer "
        "trabajo como analista de datos. Los proyectos que hice "
        "durante el programa fueron clave en mi entrevista."
    ),
    "tipo_original": "comentario",
    "score_relevancia": 90,
    "rutas": [],
    "activos_generados": {},
    "errores": [],
}


resultado = grafo.invoke(estado_inicial)


print()
print("=" * 70)
print("RESULTADO FINAL DEL GRAFO")
print("=" * 70)

print("ID:", resultado["id"])
print("Tipo original:", resultado["tipo_original"])
print("Tipo detectado:", resultado.get("tipo_detectado"))

print()
print("Sentimiento:", resultado.get("sentimiento"))
print("Tema principal:", resultado.get("tema_principal"))
print("Subtema:", resultado.get("subtema"))

print()
print("Score:", resultado.get("score_relevancia"))
print("Rutas:", resultado.get("rutas"))

print()
print("Activos:")
print(resultado.get("activos_generados"))

print()
print("Errores:", resultado.get("errores"))