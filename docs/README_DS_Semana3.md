# CommunityLab (Ó©ç ÔÇó╠Ç_ÔÇó╠ü)Ó©ç

Herramientas para convertir conversaciones de comunidades digitales en datos
analizables y activos estructurados. El flujo combina validaci├│n y relevancia
determinista con an├ílisis de lenguaje y enrutamiento por reglas.

## Flujo principal (ÔÇó╠Çß┤ùÔÇó╠ü)┘ê

```text
JSON de interacciones
    ÔåÆ limpieza y validaci├│n
    ÔåÆ puntuaci├│n de relevancia
    ÔåÆ an├ílisis estructurado con Gemini
    ÔåÆ enrutamiento con LangGraph
    ÔåÆ activos y contrato JSON de salida
```

El proyecto mantiene separadas la poblaci├│n para an├ílisis de sentimiento y la
selecci├│n de mensajes elegibles para generar contenido.

## Estructura (Ó©ç'╠Ç-'╠ü)Ó©ç

```text
configuracion/     Par├ímetros de relevancia
docs/              Arquitectura, contratos, criterios y evidencias
scripts/           Demostraciones y evaluaci├│n
src/agentes/       Cadenas, estado, grafo, nodos y contrato de salida
src/datos/         Ingesta, limpieza, relevancia y paquete de entrega
tests/             Pruebas unitarias, fixtures e integraci├│n manual
```

Puntos de entrada ├║tiles:

- `src/datos/ingesta.py`: CLI de limpieza, selecci├│n e informes.
- `src/datos/ingesta_reddit.py`: extracci├│n y transformaci├│n de entradas RSS/Atom.
- `src/agentes/procesamiento.py`: procesamiento completo del paquete de entrega.
- `src/agentes/grafo.py`: grafo de LangGraph y procesamiento por lotes.
- `src/agentes/recuperacion.py`: reprocesamiento de fallos.
- `scripts/demostracion_lotes_ciencia_datos.py`: demo de integraci├│n DA ÔåÆ DS.

## Inicio r├ípido (ÔÇó╠Ç¤ëÔÇó╠ü)┘ê

Requiere Python 3.11 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

La suite normal es offline y no necesita `GEMINI_API_KEY`.

## Evaluaci├│n de regresi├│n (ÔîÉÔûá_Ôûá)

El evaluador predeterminado compara ejecuciones guardadas y valida las rutas
contra el enrutador actual. No llama a Gemini:

```powershell
python -m scripts.evaluar_casos_ambiguos
```

Para medir el an├ílisis actual con Gemini, de forma expl├¡cita:

```powershell
python -m scripts.evaluar_casos_ambiguos --en-vivo
```

El modo en vivo requiere `GEMINI_API_KEY` en un `.env` local y consume cuota.
Los snapshots actuales son referencias hist├│ricas, no etiquetas validadas por
anotadores independientes.

## Documentaci├│n (ÔÇó╠Çß┤ùÔÇó╠ü)┘ê

- [Manual maestro de lectura del c├│digo](docs/manual_lectura_codigo.md)
- [Gu├¡a de ejecuci├│n y pruebas](docs/guia_pruebas.md)
- [Arquitectura general](docs/arquitectura_general_sistema.md)
- [Contrato de datos de ingesta](docs/contrato_datos_ingesta.md)
- [Criterio de puntuaci├│n de relevancia](docs/criterio_puntuacion_relevancia.md)
- [Acceso a fuentes de datos](docs/fuentes_de_datos_acceso.md)
