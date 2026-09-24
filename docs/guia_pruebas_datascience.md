# Guía rápida para probar Data Science

Esta guía permite validar rápidamente el módulo de **LangChain + Gemini + LangGraph** de CommunityLab.

## 1. Preparar el entorno

Desde la raíz del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Crear localmente un archivo `.env` con:

```env
GEMINI_API_KEY=TU_API_KEY
```

> `.env` ya está excluido por `.gitignore` y no debe subirse al repositorio.

---

## 2. Ejecutar las pruebas automáticas

Para validar todo el proyecto:

```powershell
python -m pytest -v
```

Para probar únicamente el router de Data Science:

```powershell
python -m pytest tests/agents/test_router_node.py -v
```

Resultado esperado: todos los tests deben aparecer como `PASSED`.

---

## 3. Probar manualmente el flujo de Data Science

### Chain de análisis

```powershell
python -m scripts.probar_chain_actualizada
```

Valida:

- sentimiento
- tema principal
- subtema
- tipo detectado

### Nodo de análisis

```powershell
python -m scripts.probar_analyzer_node
```

### Estado del agente

```powershell
python -m scripts.probar_state
```

### Flujo completo LangChain + LangGraph

```powershell
python -m scripts.probar_grafo
```

El flujo esperado es:

```text
Mensaje
  ↓
LangChain + Gemini
  ↓
Sentimiento / Tema / Subtema / Tipo
  ↓
LangGraph
  ↓
Routing
  ↓
FAQ / LinkedIn / Caso de éxito / END
```

---

## 4. Pruebas adicionales

Para ejecutar el análisis sobre el dataset de prueba:

```powershell
python -m scripts.probar_analisis_dataset
```

Para revisar los casos ambiguos usados durante el ajuste del prompt:

```powershell
python -m scripts.probar_casos_ambiguos
```

---

## Si algo falla

Comprobar primero:

1. Que el entorno `.venv` esté activado.
2. Que `requirements.txt` esté instalado.
3. Que exista `GEMINI_API_KEY` dentro de `.env`.
4. Que los comandos se ejecuten desde la raíz del proyecto.
