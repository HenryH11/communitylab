# Diagrama E2E — Semana 3

```mermaid
flowchart TD
    A[Fuentes simuladas y Reddit RSS] --> B[DA: validación y limpieza]
    B --> C[Población válida para sentimiento]
    B --> D[Selección para contenido e informe]
    C --> E[Fragmentos planos: siete campos]
    C --> F[Estados y plan de ciclos]
    D --> F
    F --> G[DS: análisis y generación condicional]
    F --> P[Remanentes pendientes]
    G --> H[preparar_entrega_resultados]
    P --> H
    H --> I[Contrato de salida DS 1.2 / 1.3]
    I --> J[Streamlit: visualización y curaduría]
    J --> K[Cloud: persistencia OCI]
    K --> L[Activos aprobados para distribución]
    J -.-> M[Adaptador al formato del brief: pendiente de acuerdo]
```

Elegible_faq y score_relevancia viajan en los estados, no en los fragmentos planos.
Fallos y pendientes se conservan explícitamente. El diagrama describe responsabilidades;
no acredita que todos los PR estén fusionados ni que la publicación sea automática.
