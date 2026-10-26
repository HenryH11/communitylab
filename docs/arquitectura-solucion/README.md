# Contratos de arquitectura

La [decisión de Semana 3](arquitectura-solucion-communitylab.md) explica las fronteras
de los tres esquemas, la compatibilidad DS 1.2/1.3 y los acuerdos pendientes.

Usar jsonschema.Draft202012Validator con jsonschema.FormatChecker(). Desde la raíz:

```sh
python -m pytest tests/test_contratos_arquitectura.py -q
```

Cada elemento de paquete["completos"]["lotes"] o paquete["contenido"]["lotes"]
cumple el intermedio. La salida DS se valida después de preparar_entrega_resultados,
no directamente sobre el resultado del grafo.
