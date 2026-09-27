# Guía de pruebas — Ciencia de Datos

Esta guía está dirigida a los integrantes del proyecto que quieran probar la rama actualizada de Ciencia de Datos.

> No es necesario crear, copiar ni modificar archivos. Todos los scripts, pruebas y archivos necesarios ya forman parte de la rama.

## 1. Qué se actualizó

La integración entre Datos y Ciencia de Datos consume directamente el paquete preparado por el equipo de Datos.

Antes, algunos programas auxiliares calculaban la relevancia y construían el `EstadoAgente` manualmente.

Ahora el flujo es:

```text
conjunto de datos
→ Datos limpia y calcula la relevancia
→ preparar_paquete_ia()
→ construir_estados_agente()
→ EstadoAgente
→ plan de ciclos por ID
→ análisis por lotes
→ elegibilidad de contenido por ID
→ enrutamiento y generación individuales
```

También se separaron explícitamente dos poblaciones:

```text
Análisis de sentimiento
→ mensajes válidos para medir la salud de la comunidad

Contenido
→ mensajes autorizados por ID para generar contenido
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

- enrutamiento;
- relevancia;
- limpieza e ingesta;
- contrato Datos → Ciencia de Datos;
- separación entre población de sentimiento y población de contenido.

Todas las pruebas deben finalizar como `PASSED`. La suite no necesita una clave
Gemini: las llamadas reales se reservan para los demos manuales.

## 4. Probar únicamente la clasificación con Gemini

```powershell
python -m scripts.demostracion_cadena_analisis
```

### Qué comprueba

Comprueba únicamente:

```text
mensaje
→ Gemini
→ sentimiento
→ tema principal
→ subtema
→ tipo_detectado
```

No prueba el enrutamiento ni la generación de contenido.

## 5. Probar el grafo completo con un mensaje controlado

```powershell
python -m scripts.demostracion_grafo_mensaje_unico
```

### Flujo que valida

Comprueba:

```text
EstadoAgente
→ análisis
→ enrutador
→ generación
```

### Qué revisar

- análisis correcto;
- rutas coherentes;
- activos reales;
- `Errores: []`.

## 6. Probar integración Datos → Ciencia de Datos con mensajes reales

```powershell
python -m scripts.demostracion_lotes_ciencia_datos
```

### Qué valida la demostración

Es la prueba principal de integración entre Datos y Ciencia de Datos.

La demostración toma los estados y `ids_contenido` de `preparar_paquete_ia()`.
Analiza `int-022` e `int-002` en una misma solicitud por lotes, y el ID decide
qué mensajes pueden generar contenido.

El flujo probado es:

```text
conjunto de datos
→ limpieza y relevancia
→ preparar_paquete_ia()
→ EstadoAgente generado por Datos
→ análisis por lotes con resultados asociados por ID
→ enrutamiento individual con `ids_contenido`
→ generación de activos
```

### Caso `int-022`

Se espera aproximadamente:

```text
Puntaje de relevancia: 95
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
Puntaje de relevancia: 80
Incluido sentimiento: True
Elegible contenido: True

Sentimiento: neutral
Tipo detectado: pregunta_tecnica
Rutas: ['preguntas_frecuentes']
Errores: []
```

Debe generarse contenido para `preguntas_frecuentes`.

## 7. Probar sentimiento sin generación de contenido

```powershell
python -m scripts.demostracion_analisis_sin_contenido
```

### Regla que comprueba

Comprueba una regla importante:

> Un mensaje puede ser válido para medir sentimiento aunque no sea suficientemente relevante para generar contenido.

La prueba utiliza `int-008`.

Se espera:

```text
Puntaje de relevancia: 39
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

Esto confirma que el mensaje sí se analiza para sentimiento, pero al no estar
en `ids_contenido` no activa ninguna ruta de generación.

## 8. Orden recomendado

Validación completa:

```powershell
python -m pytest -v
python -m scripts.demostracion_cadena_analisis
python -m scripts.demostracion_grafo_mensaje_unico
python -m scripts.demostracion_lotes_ciencia_datos
python -m scripts.demostracion_analisis_sin_contenido
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
1 pregunta frecuente
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
└── construcción del EstadoAgente
        ↓
CIENCIA DE DATOS
├── sentimiento
├── tema y subtema
├── tipo_detectado
├── enrutamiento
└── generación de activos
```

La relevancia controla la generación de contenido.

El análisis de sentimiento utiliza una población más amplia y no se limita únicamente a los mensajes seleccionados para generación.
