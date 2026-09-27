import json
import time
from pathlib import Path

from src.agents.chains import cadena_analisis


RUTA_DATASET = Path("src/data/mensajes_comunidad_simulados.json")

# Estoy usando pocas para no gastarme todos los tokens amigos xd
MAX_MENSAJES = 23


with open(RUTA_DATASET, "r", encoding="utf-8") as archivo:
    datos = json.load(archivo)


procesados = 0
coincidencias = 0
diferencias = 0
casos_diferentes = []

for lote in datos["lotes"]:

    print()
    print("#" * 80)
    print("ORIGEN:", lote["origen_comunidad"])
    print("PERIODO:", lote["periodo_referencia"])
    print("#" * 80)

    for mensaje in lote["interacciones"]:

        if procesados >= MAX_MENSAJES:
            break

        print()
        print("=" * 80)
        print("ID:", mensaje.get("id"))
        print("Autor:", mensaje["autor"])
        print("Canal:", mensaje["canal"])
        print("=" * 80)

        print("Texto:")
        print(mensaje["texto"])
        print()

        resultado = cadena_analisis.invoke(
            {
                "texto": mensaje["texto"]
            }
        )

        print("TIPO ORIGINAL :", mensaje["tipo"])
        print("TIPO IA       :", resultado.tipo_detectado)

        print("SENTIMIENTO   :", resultado.sentimiento)
        print("TEMA          :", resultado.tema)

        if mensaje["tipo"] == resultado.tipo_detectado:
            print("COMPARACIÓN   : ✅ COINCIDEN")
            coincidencias += 1

        else:
            print("COMPARACIÓN   : ⚠️ DIFERENTES")
            diferencias += 1

            casos_diferentes.append(
                {
                    "id": mensaje.get("id"),
                    "texto": mensaje["texto"],
                    "tipo_original": mensaje["tipo"],
                    "tipo_ia": resultado.tipo_detectado,
                }
            )

        procesados += 1

        # pausita 
        time.sleep(5)

    if procesados >= MAX_MENSAJES:
        break


print()
print("=" * 80)
print("RESUMEN")
print("=" * 80)

print("Mensajes procesados:", procesados)
print("Coincidencias:", coincidencias)
print("Diferencias:", diferencias)

if procesados:
    porcentaje = coincidencias / procesados * 100
    print(f"Coincidencia con dataset: {porcentaje:.1f}%")

print()
print("CASOS DIFERENTES")
print("-" * 80)

for caso in casos_diferentes:
    print()
    print("ID:", caso["id"])
    print("Texto:", caso["texto"])
    print("Original:", caso["tipo_original"])
    print("IA:", caso["tipo_ia"])