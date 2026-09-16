# Criterio de puntuación de relevancia — Sub-equipo 3 (Datos)

Primer borrador de diseño (sin implementación de código todavía) del mecanismo para
puntuar y filtrar los mejores testimonios y dudas de la comunidad antes de pasarlos
al pipeline de IA. Responsables: Gustavo Vásquez y Jhonattan Benavides.

## Objetivo

El brief oficial del proyecto (`proyecto_3_community_lab.md`) pide explícitamente un
"mecanismo de puntuación de relevancia para seleccionar los mejores momentos de la
comunidad". Dado el lote de interacciones ya limpias (ver
[`diagrama_flujo_datos_ingesta.md`](./diagrama_flujo_datos_ingesta.md)), este criterio
asigna un puntaje a cada `interacción` para quedarnos con los testimonios, preguntas
técnicas y piezas de feedback más representativos, evitando que el pipeline de IA
(Sub-equipo 2) procese ruido o contenido de bajo valor.

## Señales propuestas

| Señal | Descripción | Efecto en el puntaje |
| --- | --- | --- |
| Longitud del mensaje | Mensajes muy cortos (ej. "gracias", "ok") aportan poco contexto | Penaliza mensajes por debajo de un mínimo de caracteres/palabras |
| Palabras clave del dominio | Presencia de términos relevantes al programa (ej. "aprendí", "trabajo", "certificado", "mentor", "proyecto") | Suma puntaje por cada palabra clave detectada |
| Señal de sentimiento | Mensajes con carga emocional clara (positiva o negativa) suelen ser más útiles como testimonio o alerta | Suma puntaje a mensajes con sentimiento marcado; neutros puntúan más bajo |
| Tipo de interacción | `testimonio` y `pregunta_tecnica` son más valiosos para los objetivos del proyecto (casos de éxito y FAQ) que `comentario`/`feedback` genérico | Pondera tipo `testimonio`/`pregunta_tecnica` por encima de `comentario`/`feedback` |
| Duplicados / spam | Mensajes repetidos o con patrones de spam (enlaces sueltos, texto repetido) | Descarta o penaliza fuertemente |
| Frescura | Mensajes más recientes reflejan mejor el estado actual de la comunidad | Suma un pequeño bonus a mensajes de los últimos días |

## Regla de decisión (borrador)

1. Calcular un puntaje combinado (suma ponderada de las señales anteriores).
2. Descartar automáticamente mensajes marcados como duplicado/spam o por debajo del
   mínimo de longitud.
3. Ordenar el resto por puntaje descendente y quedarse con el top N (a definir según
   volumen real de mensajes, ej. top 20%) para pasar al pipeline de IA.

## Pendientes para Semana 1

- Definir los pesos exactos de cada señal junto con Sub-equipo 2 (para que el
  puntaje sea útil como entrada del análisis de sentimiento, no lo duplique).
- Implementar la lógica en Python como parte del script de limpieza/ingesta.
- Validar el criterio contra el archivo `src/data/mensajes_comunidad_simulados.json`.

## Notas

Borrador de Semana 0, validado contra la documentación oficial del proyecto
(`proyecto_3_community_lab.md`). Pendiente de afinar pesos junto con Sub-equipo 2.
