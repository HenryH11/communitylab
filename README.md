# CommunityLab (ง •̀_•́)ง

Herramientas para convertir conversaciones de comunidades digitales en datos
analizables y activos estructurados. El flujo combina validación y relevancia
determinista con análisis de lenguaje y enrutamiento por reglas.

## Flujo principal (•̀ᴗ•́)و

```text
JSON de interacciones
    → limpieza y validación
    → puntuación de relevancia
    → análisis estructurado con Gemini
    → enrutamiento con LangGraph
    → activos y contrato JSON de salida
```

El proyecto mantiene separadas la población para análisis de sentimiento y la
selección de mensajes elegibles para generar contenido.

## Estructura (ง'̀-'́)ง

```text
configuracion/     Parámetros de relevancia
docs/              Arquitectura, contratos, criterios y evidencias
scripts/           Demostraciones y evaluación
src/agentes/       Cadenas, estado, grafo, nodos y contrato de salida
src/datos/         Ingesta, limpieza, relevancia y paquete de entrega
tests/             Pruebas unitarias, fixtures e integración manual
```

Puntos de entrada útiles:

- `src/datos/ingesta.py`: CLI de limpieza, selección e informes.
- `src/datos/ingesta_reddit.py`: extracción y transformación de entradas RSS/Atom.
- `src/agentes/grafo.py`: procesamiento por lotes y coordinación del grafo.
- `scripts/demostracion_lotes_ciencia_datos.py`: demo de integración DA → DS.

## Inicio rápido (•̀ω•́)و

Requiere Python 3.11 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

La suite normal es offline y no necesita `GEMINI_API_KEY`.

## Evaluación de regresión (⌐■_■)

El evaluador predeterminado compara ejecuciones guardadas y valida las rutas
contra el enrutador actual. No llama a Gemini:

```powershell
python -m scripts.evaluar_casos_ambiguos
```

Para medir el análisis actual con Gemini, de forma explícita:

```powershell
python -m scripts.evaluar_casos_ambiguos --en-vivo
```

El modo en vivo requiere `GEMINI_API_KEY` en un `.env` local y consume cuota.
Los snapshots actuales son referencias históricas, no etiquetas validadas por
anotadores independientes.

## Documentación (•̀ᴗ•́)و

- [Guía de ejecución y pruebas](docs/guia_pruebas.md)
- [Arquitectura general](docs/arquitectura_general_sistema.md)
- [Contrato de datos de ingesta](docs/contrato_datos_ingesta.md)
- [Criterio de puntuación de relevancia](docs/criterio_puntuacion_relevancia.md)
- [Acceso a fuentes de datos](docs/fuentes_de_datos_acceso.md)
