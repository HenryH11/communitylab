# Guía de pruebas — Data Science

Esta guía está dirigida a los integrantes del proyecto que quieran probar la rama actualizada de Data Science.

> No es necesario crear, copiar ni modificar archivos. Todos los scripts, pruebas y archivos necesarios ya forman parte de la rama.

## 1. Qué se actualizó

La integración entre Data y Data Science ya utiliza directamente la salida preparada por Data.

Antes, algunos scripts calculaban relevancia y construían el `AgentState` manualmente.

Ahora el flujo es:

```text
dataset
→ Data limpia y calcula relevancia
→ preparar_paquete_ia()
→ construir_estados_agente()
→ AgentState
→ Data Science
→ análisis
→ routing
→ generación
```

También se separaron explícitamente dos poblaciones:

```text
Sentimiento
→ mensajes válidos para analizar la salud de la comunidad

Contenido
→ mensajes con relevancia suficiente para generar activos
```

Por eso un mensaje puede analizarse para sentimiento aunque no genere contenido.

## 2. Preparar el entorno

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Para las pruebas que utilizan Gemini, cada integrante debe tener localmente un archivo `.env` con:

```env
GEMINI_API_KEY=SU_API_KEY
```

El `.env` no debe subirse al repositorio.

## 3. Pruebas automáticas

```powershell
python -m pytest -v
```

### ¿Para qué sirve?

Comprueba la lógica determinista del proyecto:

- routing;
- relevancia;
- limpieza e ingesta;
- contrato Data → Data Science;
- separación entre población de sentimiento y población de contenido.

### Resultado esperado

En la versión actual validada:

```text
33 passed
```

Todas las pruebas deben finalizar como `PASSED`.

## 4. Probar únicamente el análisis con Gemini

```powershell
python -m scripts.probar_chain_actualizada
```

### ¿Para qué sirve?

Comprueba únicamente:

```text
mensaje
→ Gemini
→ sentimiento
→ tema principal
→ subtema
→ tipo_detectado
```

No prueba routing ni generación de activos.

## 5. Probar el grafo completo con un mensaje controlado

```powershell
python -m scripts.probar_grafo
```

### ¿Para qué sirve?

Comprueba:

```text
AgentState
→ análisis
→ router
→ generación
```

### Qué revisar

- análisis correcto;
- rutas coherentes;
- activos reales;
- `Errores: []`.

## 6. Probar integración Data → Data Science con mensajes reales

```powershell
python -m scripts.probar_grafo_2_mensajes_reales
```

### ¿Para qué sirve?

Es la prueba principal de integración entre Data y Data Science.

En esta versión, el script ya no construye manualmente el `AgentState`. Consume directamente los estados preparados por Data.

El flujo probado es:

```text
dataset
→ limpieza y relevancia
→ preparar_paquete_ia()
→ AgentState generado por Data
→ LangGraph
→ análisis
→ routing
→ generación de activos
```

### Caso `int-022`

Se espera aproximadamente:

```text
Score relevancia: 95
Incluido sentimiento: True
Elegible contenido: True

Sentimiento: muy_positivo
Tipo detectado: testimonio
Rutas: ['caso_exito', 'linkedin']
Errores: []
```

Deben generarse `caso_exito` y `linkedin`.

### Caso `int-002`

Se espera aproximadamente:

```text
Score relevancia: 80
Incluido sentimiento: True
Elegible contenido: True

Sentimiento: neutral
Tipo detectado: pregunta_tecnica
Rutas: ['faq']
Errores: []
```

Debe generarse una `faq`.

## 7. Probar sentimiento sin generación de contenido

```powershell
python -m scripts.probar_grafo_sentimiento_sin_contenido
```

### ¿Para qué sirve?

Comprueba una regla importante:

> Un mensaje puede ser válido para medir sentimiento aunque no sea suficientemente relevante para generar contenido.

La prueba utiliza `int-008`.

Se espera:

```text
Score relevancia: 39
Incluido en sentimiento: True
Elegible para contenido: False
```

Después del análisis:

```text
Rutas: []
Activos: {}
Errores: []
```

Y al final:

```text
VALIDACIÓN: OK
```

Esto confirma que el mensaje sí es analizado por Data Science, pero al no superar el umbral de relevancia no activa ninguna ruta de generación.

## 8. Orden recomendado

Validación completa:

```powershell
python -m pytest -v
python -m scripts.probar_chain_actualizada
python -m scripts.probar_grafo
python -m scripts.probar_grafo_2_mensajes_reales   ------------ESTA ES LA PRINCIPAL PARA VER TODO
python -m scripts.probar_grafo_sentimiento_sin_contenido   ------------ESTA ES LA PRINCIPAL PARA VER TODO
```

Validación rápida sin consumir Gemini:

```powershell
python -m pytest -v
```

## 9. Aclaraciones

### Las respuestas de Gemini pueden variar

No se debe esperar que títulos, resúmenes o textos generados sean exactamente iguales entre ejecuciones.

Revisar principalmente:

- clasificación coherente;
- rutas correctas;
- estructura de los activos;
- ausencia de errores;
- no invención de hechos ajenos al mensaje original.

### Algunas pruebas pueden tardar

Cuando aparezca:

```text
Procesando con LangChain + LangGraph...
```

ya comenzaron las llamadas externas a Gemini.

La prueba de dos mensajes realiza aproximadamente 5 llamadas:

```text
int-022:
1 análisis
1 caso de éxito
1 LinkedIn

int-002:
1 análisis
1 FAQ
```

Durante la validación esta prueba tardó alrededor de 3 minutos. El tiempo puede variar.

### Error 429 / ResourceExhausted

Normalmente indica límite de cuota o frecuencia de Gemini.

Esperar el tiempo indicado por la API y volver a ejecutar.

### Error 503 / ServiceUnavailable

Puede corresponder a indisponibilidad temporal del proveedor.

Esperar unos minutos y volver a ejecutar antes de asumir que hay un error en la lógica del proyecto.

## 10. Qué se valida finalmente

```text
DATA
├── limpieza
├── relevancia
├── preparación de poblaciones
└── construcción del AgentState
        ↓
DATA SCIENCE
├── sentimiento
├── tema y subtema
├── tipo_detectado
├── routing
└── generación de activos
```

La relevancia controla la generación de contenido.

El análisis de sentimiento utiliza una población más amplia y no se limita únicamente a los mensajes seleccionados para generación.
