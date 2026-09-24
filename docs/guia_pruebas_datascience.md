# Guía rápida de pruebas — Data Science V2

Esta guía corresponde al flujo actualizado de **LangChain + Gemini + LangGraph con generación real de activos**.

## Flujo actual

```text
Mensaje
  ↓
AgentState
  ↓
LangChain + Gemini
  ↓
sentimiento + tema + subtema + tipo_detectado
  ↓
LangGraph
  ↓
routing
  ↓
Caso de éxito / LinkedIn / FAQ
  ↓
contenido generado con Gemini
```

---

## 1. Preparar el entorno

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

El archivo local `.env` debe contener:

```env
GEMINI_API_KEY=TU_API_KEY
```

> `.env` está excluido mediante `.gitignore`.

---

## 2. Ejecutar las pruebas automáticas

Primero comprobar que el código determinista sigue funcionando:

```powershell
python -m pytest -v
```

Todos los tests deben finalizar como `PASSED`.

Estas pruebas no deberían depender de una respuesta real de Gemini.

---

## 3. Probar solamente la Chain de análisis

```powershell
python -m scripts.probar_chain_actualizada
```

Esta prueba valida únicamente el análisis semántico:

- sentimiento;
- tema principal;
- subtema;
- tipo detectado.

No prueba el routing ni los generadores finales.

---

## 4. Probar el grafo completo con un solo mensaje

```powershell
python -m scripts.probar_grafo
```

Esta es una prueba end-to-end con un mensaje controlado.

Valida:

```text
mensaje
→ análisis Gemini
→ AgentState
→ router
→ generación real
```

Para un testimonio relevante y muy positivo se espera:

```text
Rutas:
['caso_exito', 'linkedin']
```

Y en `Activos` deben aparecer contenidos reales, no:

```text
status: mock
```

El resultado debería incluir estructuras similares a:

```text
caso_exito:
  titular
  resumen

linkedin:
  titulo
  contenido
  canal_recomendado
```

---

## 5. Probar 2 mensajes del dataset de Datos

Archivo:

```text
scripts/probar_grafo_2_mensajes_reales.py
```

Ejecutar:

```powershell
python -m scripts.probar_grafo_2_mensajes_reales
```

La prueba utiliza dos interacciones existentes en:

```text
src/data/mensajes_comunidad_simulados.json
```

### Caso `int-022`

Es un testimonio relevante.

Se espera aproximadamente:

```text
tipo_detectado: testimonio
sentimiento: muy_positivo
rutas:
- caso_exito
- linkedin
```

Además deben generarse ambos activos con Gemini.

### Caso `int-002`

Es una pregunta técnica relevante.

Se espera aproximadamente:

```text
tipo_detectado: pregunta_tecnica
sentimiento: neutral
rutas:
- faq
```

Debe generarse una FAQ real con Gemini.

---

## 6. Importante sobre tiempos y llamadas

Esta prueba realiza varias llamadas a Gemini.

Aproximadamente:

```text
int-022
1 análisis
1 caso de éxito
1 LinkedIn
= 3 llamadas

int-002
1 análisis
1 FAQ
= 2 llamadas
```

Total aproximado:

```text
5 llamadas a Gemini
```

Por ello la ejecución puede tardar más que `probar_chain_actualizada`.

Si aparecen errores `503 ServiceUnavailable`, puede tratarse de disponibilidad temporal de la API.

---

## 7. Qué revisar en el resultado

Para cada interacción comprobar:

1. `Errores: []`
2. `tipo_detectado` coherente con el mensaje.
3. `tema_principal` y `subtema` razonables.
4. `rutas` acordes al tipo y score.
5. Los activos generados no inventan información factual.
6. No aparece `status: mock`.

---

## Orden recomendado de pruebas

```powershell
python -m pytest -v
python -m scripts.probar_chain_actualizada
python -m scripts.probar_grafo
python -m scripts.probar_grafo_2_mensajes_reales
```

Este orden permite detectar primero errores locales y luego probar progresivamente las llamadas reales al LLM.
