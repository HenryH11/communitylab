"""Pruebas offline del paquete de auditoría de Semana 4.

No realizan llamadas a proveedores de IA ni modifican archivos.
"""

import json

from src.agentes.auditoria_semana4 import (
    construir_paquete_auditoria,
    cargar_eventos_observabilidad,
    paquete_auditoria_a_json,
)


CONFIGURACION_IA = {
    "proveedor_analisis": "nvidia_nim",
    "proveedor_generacion": "nvidia_nim",
    "enrutamiento_adaptativo_activo": True,
    "modelos_nvidia_por_tier": {
        "rapido": "meta/llama-3.1-8b-instruct",
        "estandar": "google/gemma-4-31b-it",
        "razonamiento": "meta/llama-3.3-70b-instruct",
    },
    "modelo_gemini": "gemini-3.5-flash-lite",
}


def datos_fuente():
    return {
        "lotes": [
            {
                "origen_comunidad": "Discord_ONE",
                "periodo_referencia": "Semana_00",
                "interacciones": [
                    {
                        "id": "int-001",
                        "autor": "Ana",
                        "canal": "#logros",
                        "tipo": "testimonio",
                        "texto": "Conseguí mi primer trabajo.",
                        "fecha": "2026-10-14T10:00:00Z",
                        "idioma": "es",
                    },
                    {
                        "id": "int-002",
                        "autor": "Bot",
                        "canal": "#general",
                        "tipo": "comentario",
                        "texto": "spam spam spam",
                        "fecha": "2026-10-14T10:01:00Z",
                        "idioma": "es",
                    },
                ],
            }
        ]
    }


def paquete_ia():
    return {
        "informe": {
            "lotes": [
                {
                    "evaluaciones": [
                        {
                            "id": "int-001",
                            "puntaje": 90,
                            "seleccionado": True,
                            "elegible_faq": False,
                            "motivos": [],
                            "incluido_sentimiento": True,
                            "motivos_exclusion_sentimiento": [],
                        },
                        {
                            "id": "int-002",
                            "puntaje": 0,
                            "seleccionado": False,
                            "elegible_faq": False,
                            "motivos": ["texto_repetitivo"],
                            "incluido_sentimiento": False,
                            "motivos_exclusion_sentimiento": [
                                "texto_repetitivo"
                            ],
                        },
                    ]
                }
            ]
        }
    }


def salida_ds():
    return {
        "id_ejecucion": "ejecucion-001",
        "resultados": [
            {
                "id": "int-001",
                "sentimiento": "muy_positivo",
                "tema_principal": "empleabilidad",
                "subtema": "primer trabajo",
                "tipo_detectado": "testimonio",
                "es_spam_detectado": False,
                "motivo_spam": None,
                "rutas": [
                    "caso_exito",
                    "boletin",
                    "linkedin",
                ],
                "activos_generados": {
                    "linkedin": {
                        "titulo": "Un nuevo comienzo",
                        "contenido": "¡Felicitaciones, Ana! 🎉",
                        "hashtags": ["#Comunidad"],
                        "canal_recomendado": "LinkedIn Oficial",
                    }
                },
                "errores": [],
                "fallos": [],
            }
        ],
        "pendientes": [],
        "ids_pendientes": [],
    }


def eventos():
    return [
        {
            "evento": "proveedor_ia_resuelto",
            "id_ejecucion": "ejecucion-001",
            "etapa": "analizar_lote",
            "ids_interaccion": ["int-001"],
            "tier": "estandar",
            "proveedor_primario": "nvidia_nim",
            "proveedor_usado": "nvidia_nim",
            "fallback_activado": False,
            "motivo_fallback": None,
        },
        {
            "evento": "proveedor_ia_resuelto",
            "id_ejecucion": "ejecucion-001",
            "etapa": "generar_activos",
            "id_interaccion": "int-001",
            "ruta": "linkedin",
            "tier": "razonamiento",
            "proveedor_primario": "nvidia_nim",
            "proveedor_usado": "gemini",
            "fallback_activado": True,
            "motivo_fallback": "timeout",
        },
    ]


def construir():
    return construir_paquete_auditoria(
        datos_fuente=datos_fuente(),
        paquete_ia=paquete_ia(),
        salida_procesamiento=salida_ds(),
        eventos_observabilidad=eventos(),
        configuracion_ia=CONFIGURACION_IA,
        metadatos_ejecucion={
            "commit_sha": "abc123",
            "working_tree_limpio": True,
            "dataset": (
                "src/datos/"
                "mensajes_comunidad_simulados.json"
            ),
        },
    )


def test_construye_paquete_sin_modificar_contrato_productivo():
    auditoria = construir()

    assert auditoria["version_auditoria"] == "1.2"
    assert auditoria["ejecucion"]["commit_sha"] == "abc123"
    assert (
        auditoria["ejecucion"]["id_ejecucion"]
        == "ejecucion-001"
    )

    assert auditoria["resumen"]["total_entrada"] == 2
    assert auditoria["resumen"]["total_excluidas_data"] == 1
    assert auditoria["resumen"]["total_resultados_ds"] == 1
    assert auditoria["resumen"]["total_activos_generados"] == 1

    resumen = auditoria["resumen"]

    assert resumen["sentimiento_predominante"] == "muy_positivo"
    assert resumen["sentimientos_predominantes"] == [
        "muy_positivo"
    ]
    assert resumen["distribucion_sentimientos"] == {
        "muy_positivo": 1
    }
    assert resumen["temas_principales"] == [
        {
            "tema": "empleabilidad",
            "cantidad": 1,
        }
    ]
    assert resumen["distribucion_temas"] == {
        "empleabilidad": 1
    }
    assert resumen["distribucion_tipos_detectados"] == {
        "testimonio": 1
    }


def test_exclusion_data_se_conserva_por_id_y_motivo():
    auditoria = construir()

    exclusion = auditoria["exclusiones_data"][0]

    assert exclusion == {
        "id": "int-002",
        "motivos": ["texto_repetitivo"],
    }

    interaccion = next(
        item
        for item in auditoria["interacciones"]
        if item["id"] == "int-002"
    )

    assert interaccion["datos"]["excluido_por_data"] is True
    assert interaccion["analisis"] is None
    assert interaccion["activos"] == {}


def test_analisis_nvidia_conserva_modelo_del_tier():
    auditoria = construir()

    interaccion = next(
        item
        for item in auditoria["interacciones"]
        if item["id"] == "int-001"
    )

    traza = interaccion["analisis"]["trazabilidad"]

    assert traza["tier"] == "estandar"
    assert traza["proveedor_usado"] == "nvidia_nim"
    assert traza["modelo"] == "google/gemma-4-31b-it"
    assert traza["fallback_activado"] is False
    assert traza["motivo_fallback"] is None


def test_fallback_de_activo_registra_gemini_y_motivo():
    auditoria = construir()

    interaccion = next(
        item
        for item in auditoria["interacciones"]
        if item["id"] == "int-001"
    )

    traza = interaccion["activos"]["linkedin"]["trazabilidad"]

    assert traza["tier"] == "razonamiento"
    assert traza["proveedor_primario"] == "nvidia_nim"
    assert traza["proveedor_usado"] == "gemini"
    assert traza["modelo"] == "gemini-3.5-flash-lite"
    assert traza["fallback_activado"] is True
    assert traza["motivo_fallback"] == "timeout"

    resumen = auditoria["resumen"]

    assert resumen["interacciones_con_fallback_analisis"] == 0
    assert resumen["eventos_fallback_analisis"] == 0
    assert resumen["activos_con_fallback"] == 1
    assert resumen["eventos_fallback_generacion"] == 1


def test_resumen_distingue_eventos_de_interacciones_con_fallback():
    lista_eventos = eventos()

    evento_analisis = dict(lista_eventos[0])
    evento_analisis.update(
        proveedor_usado="gemini",
        fallback_activado=True,
        motivo_fallback="timeout",
    )

    # Simula dos eventos reales de fallback sobre la misma
    # interacción, por ejemplo debido a un reprocesamiento.
    lista_eventos[0] = dict(evento_analisis)
    lista_eventos.insert(
        0,
        dict(evento_analisis),
    )

    auditoria = construir_paquete_auditoria(
        datos_fuente=datos_fuente(),
        paquete_ia=paquete_ia(),
        salida_procesamiento=salida_ds(),
        eventos_observabilidad=lista_eventos,
        configuracion_ia=CONFIGURACION_IA,
        metadatos_ejecucion={
            "commit_sha": "abc123",
            "working_tree_limpio": True,
            "dataset": (
                "src/datos/"
                "mensajes_comunidad_simulados.json"
            ),
        },
    )

    resumen = auditoria["resumen"]

    assert resumen[
        "interacciones_con_fallback_analisis"
    ] == 1

    assert resumen[
        "eventos_fallback_analisis"
    ] == 2


def test_no_hay_inconsistencias_con_evidencia_completa():
    auditoria = construir()

    assert auditoria["inconsistencias"] == []
    assert auditoria["resumen"]["total_inconsistencias"] == 0


def test_detecta_activo_sin_trazabilidad():
    lista_eventos = eventos()[0:1]

    auditoria = construir_paquete_auditoria(
        datos_fuente=datos_fuente(),
        paquete_ia=paquete_ia(),
        salida_procesamiento=salida_ds(),
        eventos_observabilidad=lista_eventos,
        configuracion_ia=CONFIGURACION_IA,
        metadatos_ejecucion={
            "commit_sha": "abc123",
            "working_tree_limpio": True,
            "dataset": "dataset.json",
        },
    )

    assert {
        "id": "int-001",
        "ruta": "linkedin",
        "tipo": "activo_sin_trazabilidad",
    } in auditoria["inconsistencias"]


def test_carga_solo_eventos_de_la_ejecucion_correcta(tmp_path):
    ruta = tmp_path / "ciencia_datos.jsonl"

    registros = [
        {
            "evento": "proveedor_ia_resuelto",
            "id_ejecucion": "ejecucion-001",
            "id_interaccion": "int-001",
        },
        {
            "evento": "llm_fin",
            "id_ejecucion": "ejecucion-001",
        },
        {
            "evento": "proveedor_ia_resuelto",
            "id_ejecucion": "otra-ejecucion",
            "id_interaccion": "int-999",
        },
    ]

    ruta.write_text(
        "\n".join(
            json.dumps(registro, ensure_ascii=False)
            for registro in registros
        ),
        encoding="utf-8",
    )

    encontrados = cargar_eventos_observabilidad(
        ruta,
        id_ejecucion="ejecucion-001",
    )

    assert len(encontrados) == 1
    assert encontrados[0]["id_interaccion"] == "int-001"


def test_serializacion_preserva_unicode():
    texto = paquete_auditoria_a_json(construir())

    assert "¡Felicitaciones, Ana! 🎉" in texto
    assert "\\ud83c" not in texto


def test_auditoria_conserva_campos_spam():
    auditoria = construir()

    interaccion = next(
        item
        for item in auditoria["interacciones"]
        if item["id"] == "int-001"
    )

    analisis = interaccion["analisis"]

    assert "es_spam_detectado" in analisis
    assert "motivo_spam" in analisis
    assert analisis["es_spam_detectado"] is False
    assert analisis["motivo_spam"] is None
