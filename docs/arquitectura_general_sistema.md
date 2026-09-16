# Arquitectura general del sistema — CommunityLab

Aproximación de la arquitectura completa del proyecto (los 4 sub-equipos definidos
en la reunión de Semana 0), para ubicar el aporte de Ingesta y Procesamiento de
Datos (Sub-equipo 3: Gustavo Vásquez y Jhonattan Benavides) dentro del pipeline
general. El diagrama detallado del tramo de ingesta está en
[`diagrama_flujo_datos_ingesta.md`](./diagrama_flujo_datos_ingesta.md); este
documento da la vista de conjunto.

## Diagrama

```mermaid
flowchart TD
    subgraph S3["Sub-equipo 3 · Ingesta y Datos (Gustavo, Jhonattan) ← NOSOTROS"]
        A[Fuentes de la comunidad<br/>Discord / Slack / Foros / GitHub / Formularios]
        B[Ingesta por lote<br/>origen_comunidad + periodo_referencia + interacciones]
        C[Limpieza y deduplicado]
        D[Puntuación de relevancia<br/>testimonio / pregunta_tecnica / comentario / feedback]
        A --> B --> C --> D
    end

    subgraph S2["Sub-equipo 2 · Cerebro de IA (Danny, Arnold)"]
        E[Grafo LangGraph/LangChain]
        F[Análisis de sentimiento<br/>y clasificación de temas]
        G[Generación de copy<br/>LinkedIn / Newsletter / FAQ]
        E --> F --> G
    end

    subgraph S1["Sub-equipo 1 · Dirección, Arquitectura y Front-End (Enrique, Nelson, Sebastián)"]
        H[Interfaz Streamlit/Gradio<br/>panel de curaduría y aprobación]
    end

    subgraph S4["Sub-equipo 4 · Infraestructura y Nube (Marco, Renato)"]
        I[OCI Object Storage<br/>bucket Always Free]
        J[OCI Compute Instance<br/>opcional: despliegue completo]
    end

    D -->|JSON de interacciones filtradas| E
    G --> H
    H --> I
    G -.->|activos generados| I
    I -.-> J

    classDef nosotros fill:#2b6cb0,color:#fff,stroke:#1a365d,stroke-width:2px;
    class A,B,C,D nosotros
```

## Ubicación de nuestro aporte

Sub-equipo 3 es el **punto de entrada** del pipeline: todo lo que llega de la
comunidad pasa primero por nuestro tramo (ingesta → limpieza → puntuación de
relevancia) antes de convertirse en el JSON que consume el Sub-equipo 2 para el
análisis de IA. Cualquier problema de calidad de datos aquí se propaga a todo el
resto del sistema, por lo que el esquema de entrada (`origen_comunidad` /
`periodo_referencia` / `interacciones`) y el criterio de relevancia son las piezas
más críticas de esta etapa.

## Notas

- Vista de conjunto en Semana 0, basada en la estructura de sub-equipos y el flujo
  descrito en `proyecto_3_community_lab.md` y en la reunión del 14 de septiembre.
- Nelson (Solution Architect) es quien valida/ajusta el diagrama de arquitectura
  definitivo del sistema; este documento es el aporte de datos a esa definición.
