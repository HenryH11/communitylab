# GUÍA EJECUCIÓN — DATA SCIENCE SEMANA 2

## ¿Para qué sirve?

Esta guía permite ejecutar la prueba funcional completa del módulo de Data Science:

```text
Data
    ↓
Data Science + Gemini
    ↓
LangGraph
    ↓
Routing
    ↓
Generación de activos
    ↓
Contrato oficial de salida DS v1.1
```

La prueba utiliza las 23 interacciones del dataset de demostración y genera la salida consolidada de Data Science.

---

## 1. Abrir PowerShell

Abrir una terminal PowerShell en la raíz del proyecto.

---

## 2. Crear el entorno virtual

Solo si todavía no existe:

```powershell
python -m venv .venv
```

---

## 3. Activar el entorno virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 4. Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

---

## 5. Configurar Gemini

Crear o configurar el archivo `.env` en la raíz del proyecto:

```text
GEMINI_API_KEY="tu_api_key"
```

Si requieren una API Key, pueden crear una propia o solicitar una al equipo.

No subir el archivo `.env` al repositorio.

---

## 6. Configurar UTF-8 en Windows

Para evitar problemas con tildes y caracteres especiales:

```powershell
$env:PYTHONUTF8="1"
```

---

## 7. Ejecutar la prueba funcional completa

```powershell
python -B -m pytest tests\integracion\prueba_entrega_resultados_funcional.py -v -s -p no:cacheprovider
```

La prueba ejecuta:

```text
23 interacciones recibidas desde Data
        ↓
Análisis con Gemini
        ↓
Sentimiento + tema + subtema + tipo_detectado
        ↓
LangGraph
        ↓
Routing determinista
        ↓
Generación de activos
        ↓
Contrato oficial DS v1.1
```

La ejecución puede tomar algunos minutos debido al control de solicitudes implementado para reducir errores `429 RESOURCE_EXHAUSTED` de Gemini.

---

## 8. Archivos generados

Al finalizar se generan:

```text
output\entrega_ciencia_datos_completa.json
output\resumen_entrega_ciencia_datos.txt
```

El archivo principal es:

```text
output\entrega_ciencia_datos_completa.json
```

El contrato de salida actual es la versión:

```text
1.1
```

y contiene:

- `resumen_comunidad`
- `interacciones`
- `activos`
- `pendientes`
- `ids_pendientes`

Cada interacción conserva, entre otros campos:

- `tipo_original`
- `score_relevancia`
- `elegible_contenido`
- `elegible_faq`
- `sentimiento`
- `tema_principal`
- `subtema`
- `tipo_detectado`
- `rutas`
- `activos_generados`
- `errores`

---

# RESULTADO ESPERADO CON DATA ACTUALIZADO

Este resultado corresponde al flujo integrado con la versión de Data que incorpora `pregunta_programa` y `elegible_faq`.

```text
23 interacciones procesadas
0 pendientes
19 elegibles para contenido
5 elegibles para FAQ
19 interacciones con activos
35 activos generados
0 errores
```

Pytest debe finalizar con:

```text
1 passed
```

Puede aparecer un `DeprecationWarning` proveniente de `google.genai`. Esta advertencia no impide la ejecución funcional.

---

## Distribución esperada de activos

### Testimonios

8 testimonios generan 24 activos:

```text
8 caso_exito
8 boletin / Community Highlight
8 linkedin
```

### Preguntas técnicas

4 preguntas técnicas generan:

```text
4 preguntas_frecuentes
```

### Preguntas del programa

5 preguntas del programa con `elegible_faq=true` generan:

```text
5 preguntas_frecuentes
```

Los casos validados son:

```text
int-004
int-007
int-010
int-013
int-015
```

La regla utilizada es:

```text
pregunta_programa
+
elegible_faq = true
        ↓
preguntas_frecuentes
```

Las FAQ de programa deben evitar inventar:

- precios;
- fechas;
- condiciones;
- beneficios;
- alianzas;
- procedimientos;
- información institucional no proporcionada.

Cuando la información no está disponible, la respuesta debe indicar que se confirme mediante una fuente oficial vigente.

### Feedback

2 interacciones de feedback generan:

```text
2 insight_mejora
```

### Total

```text
24 activos de testimonios
+ 4 FAQ técnicas
+ 5 FAQ de programa
+ 2 insight_mejora
= 35 activos
```

---

# ACLARACIÓN SOBRE LA INTEGRACIÓN CON DATA

Data Science no calcula `elegible_faq`.

Ese campo es generado previamente por Data y Data Science únicamente lo consume para el routing.

La integración fue validada utilizando la rama completa del equipo de Data, obteniendo:

```text
79 passed
124 subtests passed
0 failures
```

y posteriormente el E2E completo con Gemini:

```text
23 procesadas
19 elegibles para contenido
5 elegibles para FAQ
35 activos
0 errores
1 passed
```

## Si el cambio de Data todavía no está integrado

El código de Data Science mantiene compatibilidad con paquetes anteriores.

Si se ejecuta esta prueba antes de incorporar la versión de Data que entrega `elegible_faq`, el contrato seguirá funcionando, pero los mensajes de `pregunta_programa` tendrán:

```text
elegible_faq: false
```

y no generarán FAQ.

En ese escenario anterior pueden observarse aproximadamente:

```text
14 interacciones con activos
30 activos generados
0 elegibles para FAQ
```

Esto no representa un error de Data Science; indica que se está ejecutando todavía con el paquete anterior de Data.

---

# PRUEBAS RÁPIDAS SIN EJECUTAR EL E2E COMPLETO

## Router

```powershell
python -m pytest tests\agents\test_enrutador.py -q
```

Resultado validado:

```text
11 passed
```

## Prompts de generadores

```powershell
python -m pytest tests\agents\test_prompts_generadores.py -q
```

Resultado validado:

```text
6 passed
```

## Ambas pruebas

```powershell
python -m pytest tests\agents\test_enrutador.py tests\agents\test_prompts_generadores.py -q
```

Resultado validado:

```text
17 passed
```

Estas pruebas no reemplazan el E2E, pero permiten validar rápidamente el routing y los prompts antes de consumir cuota de Gemini.

---

# QUÉ REVISAR EN EL JSON FINAL

En `output\entrega_ciencia_datos_completa.json`, comprobar:

```text
version_contrato = 1.1
total_interacciones_procesadas = 23
total_pendientes = 0
total_elegibles_contenido = 19
total_elegibles_faq = 5
total_con_activos = 19
total_activos_generados = 35
total_con_errores = 0
```

Para `int-004`, `int-007`, `int-010`, `int-013` e `int-015`, comprobar:

```text
tipo_original = pregunta_programa
elegible_faq = true
tipo_detectado = pregunta_programa
rutas = ["preguntas_frecuentes"]
```

También revisar que cada uno tenga un activo:

```text
activos_generados.preguntas_frecuentes
```

y que la respuesta no invente información institucional.
