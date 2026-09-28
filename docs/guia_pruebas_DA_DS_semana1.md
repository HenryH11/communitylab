# Guía de pruebas — Integración DA–DS Semana 1

Esta guía permite validar la rama `feature/DA-DS-Semana1` 

> **Prueba recomendada de flujo completo:**  
> `python -m scripts.demostracion_lotes_ciencia_datos`

## 1. Preparar el entorno

Ubicarse en la raíz del proyecto y activar el entorno virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Si todavía no existe:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Para las pruebas reales con Gemini debe existir localmente:

```text
GEMINI_API_KEY=...
```

en `.env`.

**No subir `.env` ni compartir la clave.**

Comprobación opcional:

```powershell
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('GEMINI_API_KEY cargada:', bool(os.getenv('GEMINI_API_KEY')))"
```

Resultado esperado:

```text
GEMINI_API_KEY cargada: True
```

## 2. Ejecutar la suite completa

### ¿Para qué sirve?

Comprueba integración, procesamiento de Datos, análisis por lotes, routing, almacenamiento y demás pruebas automatizadas.

```powershell
python -B -m pytest -q -p no:cacheprovider
```

### Resultado de referencia

```text
87 passed
106 subtests passed
0 failures
```

Pueden aparecer warnings de LangChain/LangGraph o deprecaciones de Python sin que la prueba haya fallado.

## 3. Verificar sintaxis

```powershell
python -c "from pathlib import Path; archivos=[p for raiz in ('src','scripts','tests') for p in Path(raiz).rglob('*.py')]; [compile(p.read_text(encoding='utf-8'), str(p), 'exec') for p in archivos]; print(f'OK - {len(archivos)} archivos Python compilan')"
```

En la revisión actual se validaron 33 archivos.

## 4. Verificar CLI

```powershell
python -m src.datos.ingesta --help
```

Debe mostrar opciones como:

```text
--entrada
--salida
--informe
--configuracion
--fecha-referencia
--maximo-por-lote
--puntaje-minimo
--tamano-ciclo
--ciclos
--entrega-ia
```

También:

```powershell
python -m src.datos.ingesta_reddit --help
```

Debe mostrar opciones como:

```text
--comunidad
--publicaciones
--comentarios-por-publicacion
--periodo-referencia
--salida
--agente-usuario
--idioma
```

Los aliases anteriores siguen disponibles internamente por compatibilidad, pero no aparecen en `--help`.

## 5. Prueba principal: flujo completo Data → DS → LangGraph → Gemini

Esta es la prueba recomendada para demostrar el flujo integrado de punta a punta:

```powershell
python -m scripts.demostracion_lotes_ciencia_datos
```

### ¿Qué valida?

```text
Datos
  ↓
preparar_paquete_ia()
  ↓
estados + plan + ids_contenido
  ↓
procesar_estados_por_lotes()
  ↓
análisis con Gemini
  ↓
routing determinista
  ↓
generación de activos
```

### Caso `int-022`

Debe mostrar aproximadamente:

```text
Tipo original: testimonio
Puntaje de relevancia: 95
Incluido sentimiento: True
Elegible contenido: True
Sentimiento: muy_positivo
Tema principal: empleabilidad
Tipo detectado: testimonio
Rutas: ['caso_exito', 'linkedin']
Errores: []
```

Además deben generarse:

```text
[caso_exito]
[linkedin]
```

### Caso `int-002`

Debe mostrar aproximadamente:

```text
Tipo original: pregunta_tecnica
Puntaje de relevancia: 80
Incluido sentimiento: True
Elegible contenido: True
Sentimiento: neutral
Tema principal: datos_ia
Tipo detectado: pregunta_tecnica
Rutas: ['preguntas_frecuentes']
Errores: []
```

Y debe generarse:

```text
[preguntas_frecuentes]
```

### ¿Qué revisar en los activos?

**LinkedIn**
- usa información del mensaje original;
- no inventa empresas, cargos o resultados;
- genera un título propio;
- utiliza hashtags relacionados;
- evita copiar literalmente el few-shot.

**Caso de éxito**
- separa el hecho de la percepción de la persona;
- evita causalidades no sustentadas como `gracias a`, `fue determinante` o `permitió conseguir`.

**Preguntas frecuentes**
- respuesta breve y didáctica;
- no inventa contexto técnico;
- si falta información, indica qué dato sería necesario.

## 6. Validar sentimiento sin generación de contenido

```powershell
python -m scripts.demostracion_analisis_sin_contenido
```

### ¿Para qué sirve?

Comprueba la separación entre mensajes válidos para sentimiento y mensajes elegibles para contenido.

El caso de referencia es `int-008`.

Resultado esperado:

```text
Elegible contenido: False
Rutas: []
Activos generados: {}
Errores: []
```

Esto valida que `ids_contenido` se respeta antes de generar activos.

## 7. Arquitectura DA → DS validada

Data prepara el paquete con:

```python
from src.datos.ingesta import cargar_json
from src.datos.entrega_ia import preparar_paquete_ia
```

Data Science consume ese contrato con:

```python
from src.agentes.grafo import procesar_paquete_entrega
```

Flujo:

```text
Data
preparar_paquete_ia()
        ↓
      paquete
        ↓
Data Science
procesar_paquete_entrega()
        ↓
análisis por lotes
        ↓
routing
        ↓
generación
```

`procesar_paquete_entrega()` se encarga de:

- validar IDs;
- respetar `plan["ids_contenido"]`;
- seguir los ciclos definidos por Data;
- conservar pendientes;
- subdividir el análisis en lotes de máximo 10 mensajes;
- devolver resultados y resultados indexados por ID.

No es necesario recorrer manualmente cada ciclo llamando `grafo.invoke()` mensaje por mensaje.

## 8. Pruebas adicionales opcionales

```powershell
python -m scripts.demostracion_cadena_analisis
python -m scripts.demostracion_grafo_mensaje_unico
python -m scripts.demostracion_nodo_analizador
python -m scripts.evaluar_casos_ambiguos
python -m scripts.evaluar_conjunto_datos
```

Estas pruebas son útiles para diagnóstico, pero no sustituyen la prueba completa de la sección 5.

## 9. Orden recomendado

1. Suite completa:

```powershell
python -B -m pytest -q -p no:cacheprovider
```

2. Flujo completo:

```powershell
python -m scripts.demostracion_lotes_ciencia_datos
```

3. Sentimiento sin contenido:

```powershell
python -m scripts.demostracion_analisis_sin_contenido
```

4. CLI y pruebas adicionales, si se desea.

## 10. Observaciones conocidas

### Rate limits de Gemini

El sistema limita el análisis a un máximo de 10 mensajes por solicitud:

```text
MAX_INTERACCIONES_POR_SOLICITUD = 10
```

Eso limita el tamaño del batch, pero no constituye por sí solo un control completo del rate limit del proveedor.

Si Gemini responde con `429` o `503`, puede tratarse de cuota, saturación o disponibilidad temporal.

El throttling por RPM y un backoff específico para esos errores quedan como mejora operativa posterior.

### Warnings

Pueden aparecer advertencias de deprecación de LangChain/LangGraph o Python durante `pytest`. Mientras la suite termine sin `FAILED` ni `ERROR`, no representan un fallo de esta integración.

## Validación esperada para aprobar el PR

Como mínimo:

```text
Suite completa                     OK
Flujo Data → DS → LangGraph        OK
int-022 → caso_exito + linkedin    OK
int-002 → preguntas_frecuentes     OK
Sentimiento sin contenido          OK
Errores de ejecución               []
```

Si estos puntos se cumplen, el flujo principal de Semana 1 queda validado.
