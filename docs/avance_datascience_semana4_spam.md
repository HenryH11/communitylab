# Avance Data Science — Semana 4: detección semántica de spam

**Proyecto:** CommunityLab — Hackathon ONE G10 / Equipo 39

**Subequipo:** Cerebro de IA (Data Science)

**Rama de trabajo:** `feature/DS-Semana4-Spam`

**Commit de implementación:** `be2c971cff690f58f7107a091172b7591f4b32cb`

**Estado:** implementación publicada y pruebas locales aprobadas; contrato v1.4 pendiente de conformidad formal de SS/QA.

## 1. Objetivo y alcance

Incorporar detección **semántica** de spam al análisis de las interacciones de la comunidad, sin reemplazar la clasificación de sentimiento, tema o tipo de mensaje ni alterar las decisiones calculadas por Data.

La implementación busca:

- identificar mensajes con intención de promoción no solicitada, captación, engaño u ofertas dudosas;
- evitar falsos positivos por simples menciones de dinero, salarios, empleo, certificaciones o fraudes;
- impedir que las interacciones detectadas como spam generen rutas o activos;
- conservar la decisión y su justificación en la salida estructurada;
- separar el spam de la distribución agregada de sentimiento;
- entregar los campos nuevos mediante el contrato DS **v1.4**, con validación de formatos históricos **v1.2** y **v1.3**.

**Límite de responsabilidad:** Data mantiene la autoridad sobre `score_relevancia`, `tipo_original`, `elegible_contenido`, `elegible_faq` y la deduplicación. Data Science consume esos valores, conserva `tipo_original` y produce `tipo_detectado` y los campos de spam. El indicador de spam no recalcula ni sustituye las decisiones de Data.

## 2. Flujo implementado

```text
Datos / paquete IA
       |
       v
Análisis LLM individual o por lote
(sentimiento, tema, subtema, tipo_detectado,
 es_spam_detectado, motivo_spam)
       |
       v
Validación estructurada (Pydantic)
       |
       v
LangGraph / enrutador
       |--- es_spam_detectado == true ---> rutas = []
       |                                     sin activos generados
       |
       `--- no spam ---> reglas de rutas y elegibilidad existentes
       |
       v
Validación de entrega + resumen comunitario
       |
       v
Contrato DS v1.4 para consumidores posteriores
```

La detección se añade a los prompts de `src/agentes/prompts/analisis.py`. La plantilla por lotes reutiliza el mismo mensaje de sistema que el análisis individual. La respuesta se valida con `AnalisisMensaje` y, en lotes, con `AnalisisLote` en `src/agentes/modelos.py`.

## 3. Criterios de clasificación

La etiqueta de spam es **independiente** del sentimiento, tema, subtema y tipo de interacción. No se incorpora una categoría de sentimiento denominada «spam».

Se considera evidencia positiva de spam una intención de promoción no solicitada, captación, engaño u oferta dudosa, evaluando el contenido completo. Por el contrario, **no basta** mencionar un sueldo, un precio, una certificación, oportunidades laborales o una estafa: la intención comunicativa puede ser legítima.

| Ejemplo resumido | Comportamiento esperado |
| --- | --- |
| «Gana 500 dólares diarios sin experiencia. Escríbeme al privado» | `es_spam_detectado = true`, con motivo |
| «Cuidado con el mensaje que promete 500 dólares diarios; es una estafa» | `false`, `motivo_spam = null` |
| «Conseguí empleo como analista con un salario de 2500 soles» | `false`, permite routing legítimo |
| «¿Cuánto cuesta el examen OCI y los servicios cloud?» | `false`, conserva su tratamiento como consulta |

Estos ejemplos son **casos de aceptación estructural**: las pruebas automatizadas de `test_spam_aceptacion.py` simulan clasificaciones previamente obtenidas. No miden por sí mismas la precisión semántica real del LLM.

## 4. Modelo de análisis y validaciones

Se agregaron dos campos **obligatorios** para todo análisis exitoso:

| Campo | Tipo | Regla |
| --- | --- | --- |
| `es_spam_detectado` | `bool` estricto | Solo `true` o `false`, no texto ni conversiones implícitas |
| `motivo_spam` | `str \| None` | Si hay spam: explicación no vacía de hasta 160 caracteres; si no hay spam: `None`/`null` |

El modelo `AnalisisMensaje` aplica estas restricciones con Pydantic. `src/agentes/validacion_entrega.py` comprueba nuevamente la coherencia antes de generar una entrega pública. Cuando el análisis ha fallado y contiene `errores`, no se exige inventar resultados de spam.

Ejemplo conceptual de análisis estructurado con spam:

```json
{
  "sentimiento": "neutral",
  "tema_principal": "otros",
  "subtema": "oferta de ingresos",
  "tipo_detectado": "comentario",
  "es_spam_detectado": true,
  "motivo_spam": "Promesa de ingresos rápidos con captación privada"
}
```

Este es un **ejemplo de formato**, no una respuesta literal certificada de una corrida en vivo.

## 5. Efecto sobre las rutas y los activos

`src/agentes/nodos/nodo_enrutador.py` evalúa `es_spam_detectado` **antes** de las reglas basadas en tipo, sentimiento, relevancia y elegibilidad:

- Si el valor es `True`, devuelve `rutas = []` y `tier_modelo = rapido`.
- No se seleccionan rutas de LinkedIn, boletín, caso de éxito, FAQ o insight de mejora para esa interacción.
- Si el valor no es `True`, continúa el enrutamiento determinista existente, sujeto a las decisiones de Data.

Por tanto, incluso un mensaje con puntuación de relevancia alta o `elegible_faq = true` queda bloqueado si DS lo identifica como spam. Esta protección **no elimina ni modifica** la interacción original.

## 6. Resumen y contrato de salida v1.4

En `src/agentes/entrega_resultados.py` se conservan `es_spam_detectado` y `motivo_spam` en cada interacción entregada. `src/agentes/resumen_entrega.py` agrega `total_spam_detectado`.

**Regla de agregación:** las interacciones con `es_spam_detectado is True` se excluyen de `distribucion_sentimientos`, `sentimiento_predominante` y `sentimientos_predominantes`. Siguen contabilizadas en `total_interacciones_procesadas` y, salvo otra regla específica, en los demás recuentos de temas o tipos. No se afirma que desaparezcan de toda agregación.

Ejemplo ilustrativo de un fragmento de entrega:

```json
{
  "version_contrato": "1.4",
  "resumen_comunidad": {
    "total_interacciones_procesadas": 2,
    "total_spam_detectado": 1,
    "distribucion_sentimientos": {"neutral": 1}
  },
  "interacciones": [
    {
      "id": "spam-001",
      "es_spam_detectado": true,
      "motivo_spam": "Captación mediante oferta dudosa",
      "rutas": [],
      "activos_generados": {}
    },
    {
      "id": "normal-001",
      "es_spam_detectado": false,
      "motivo_spam": null
    }
  ]
}
```

**Nota:** el fragmento anterior omite por brevedad campos obligatorios del contrato; no debe utilizarse directamente como una entrega validable.

Los tipos Python del contrato se definen en `src/agentes/contrato_salida_ciencia_datos.py`. El esquema compartido está en `docs/arquitectura-solucion/contrato-salida.schema.json`:

- **v1.2:** formato histórico sin campos introducidos en v1.3 ni en v1.4;
- **v1.3:** campos de ejecución y reintentos, sin campos de spam;
- **v1.4:** conserva los campos de v1.3; exige `total_spam_detectado` en el resumen y `es_spam_detectado`/`motivo_spam` en las interacciones analizadas correctamente;
- una interacción con errores puede omitir los campos analíticos que no se pudieron producir.

La compatibilidad histórica se comprobó mediante pruebas de validación de contratos; **no** significa que la función productiva actual emita automáticamente una salida en v1.2 o v1.3.

## 7. Pruebas y evidencia

Resultados obtenidos localmente sobre la rama de Semana 4:

| Validación | Resultado | Alcance |
| --- | --- | --- |
| `tests/agents/` | **302 passed** | Regresión offline DS: análisis simulado, modelos, routing, entrega, proveedores, errores y auditoría |
| `tests/test_contratos_arquitectura.py` | **19 passed** | Validez del JSON Schema, contrato v1.4 y compatibilidad histórica v1.2/v1.3 |
| Pruebas exploratorias con LLM | **4 casos observados** | Spam promocional y tres casos legítimos; no constituyen una métrica estadística de exactitud |

En la exploración con LLM se observaron las clasificaciones esperadas para una oferta sospechosa, una advertencia contra fraude, un testimonio laboral con salario y una consulta sobre costes de OCI/cloud. La trazabilidad de una invocación adicional registró `proveedor_usado = nvidia_nim` y `fallback_activado = false`; ese dato **solo acredita esa invocación**, no el proveedor efectivo de las otras cuatro.

Las pruebas offline no necesitan credenciales ni deben confundirse con evaluaciones humanas. Los resultados históricos de evaluación y los fixtures candidatos **no son ground truth humano**.

### Reproducir validaciones offline en PowerShell

Desde la raíz del repositorio, con el entorno virtual ya activado:

```powershell
@'
import os
import pytest

os.environ["PYTHON_DOTENV_DISABLED"] = "1"
for clave in (
    "NVIDIA_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "COMMUNITYLAB_MODELO_NVIDIA",
    "COMMUNITYLAB_MODELO_NVIDIA_RAPIDO",
    "COMMUNITYLAB_MODELO_NVIDIA_ESTANDAR",
    "COMMUNITYLAB_MODELO_NVIDIA_RAZONAMIENTO",
    "COMMUNITYLAB_ENRUTAMIENTO_ADAPTATIVO",
):
    os.environ.pop(clave, None)

raise SystemExit(pytest.main([
    "tests/agents/",
    "tests/test_contratos_arquitectura.py",
    "-q", "-x", "-p", "no:cacheprovider",
]))
'@ | python -B -
```

El aislamiento de variables se aplica **solo al proceso de prueba** y no edita `.env`. El número total de pruebas puede cambiar cuando la rama evolucione. Las pruebas automatizadas utilizan mocks donde corresponde y no deben interpretarse como llamadas reales a NVIDIA NIM o Gemini.

Pruebas relevantes: `test_modelo_spam.py`, `test_spam_aceptacion.py`, `test_resumen_spam.py`, `test_validacion_entrega_spam.py`, `test_enrutador.py` y `tests/test_contratos_arquitectura.py`.

## 8. Proveedores, fallos y responsabilidades

El flujo configurado para esta línea de trabajo utiliza **NVIDIA NIM como primario** y **Gemini como respaldo**, sujeto a la configuración efectiva de ejecución. La mejora de spam reutiliza este mecanismo; no introduce un proveedor diferente ni altera la estrategia estable.

Conviene distinguir:

1. **Retry:** repetición de una invocación ante errores transitorios según las políticas configuradas.
2. **Fallback de proveedor:** invocación del respaldo cuando falla el primario bajo las condiciones previstas.
3. **Recuperación posterior:** reprocesamiento de elementos que permanecen fallidos tras la ejecución.

Los análisis fallidos se registran como errores/fallos; no se etiquetan automáticamente como spam ni se fuerza una clasificación inexistente.

## 9. Limitaciones y pendientes

- La detección por LLM es probabilística: pueden existir falsos positivos y falsos negativos; requiere evaluación ampliada con ejemplos representativos y anotación humana.
- Los cuatro casos en vivo son una **prueba exploratoria limitada**. No permiten calcular precisión, recall o F1 de detección de spam.
- La deduplicación y el filtrado inicial pertenecen a Data; esta implementación no los reemplaza.
- El resumen excluye spam del **sentimiento agregado**, pero no de todas las distribuciones.
- El JSON Schema v1.4 se publicó en la rama DS y sus pruebas locales pasaron; está **pendiente la revisión y conformidad formal de SS/QA** antes del merge a `develop`.
- No se ha realizado merge a `develop` ni corresponde iniciar la siguiente etapa hasta completar la coordinación.

## 10. Archivos principales y trazabilidad

| Área | Archivos |
| --- | --- |
| Modelos y prompts | `src/agentes/modelos.py`, `src/agentes/prompts/analisis.py` |
| Enrutamiento | `src/agentes/nodos/nodo_enrutador.py` |
| Propagación / entrega | `src/agentes/estado_agente.py`, `src/agentes/entrega_resultados.py`, `src/agentes/validacion_entrega.py` |
| Resumen | `src/agentes/resumen_entrega.py` |
| Contratos | `src/agentes/contrato_salida_ciencia_datos.py`, `docs/arquitectura-solucion/contrato-salida.schema.json` |
| Pruebas nuevas | `tests/agents/test_modelo_spam.py`, `tests/agents/test_spam_aceptacion.py`, `tests/agents/test_resumen_spam.py`, `tests/agents/test_validacion_entrega_spam.py` |

**Commit técnico publicado:** `be2c971cff690f58f7107a091172b7591f4b32cb`. Este documento se incorpora posteriormente como complemento documental del mismo desarrollo, sin modificar el commit técnico original.
