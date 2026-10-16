"""Auditor semántico de DA contra los casos sintéticos de la Semana 4.

Las variantes del fixture traen la decisión humana esperada: las "revisar" deben
producir al menos una alerta y las "aceptable" ninguna. Sin red ni modelos de IA.
"""

import json
from pathlib import Path

import pytest

from scripts.auditoria_consistencia import (
    a_markdown, auditar_activo, auditar_casos, auditar_entrega, principal, resumen,
)


RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / "tests/fixtures/casos_consistencia_semana4.json"
CASOS = json.loads(FIXTURE.read_text(encoding="utf-8"))
SIN_OPCIONES = {"excluidas": [], "fuentes": []}
FILAS = auditar_casos(CASOS, SIN_OPCIONES)


@pytest.mark.parametrize("fila", FILAS, ids=lambda f: f"{f['id_interaccion']}-{f['ruta']}")
def test_decision_sugerida_coincide_con_la_esperada(fila):
    esperado_revisar = fila["esperado"] == "revisar"
    assert (fila["decision_sugerida"] == "revisar") is esperado_revisar, fila["alertas"]


@pytest.mark.parametrize(
    ("variante", "tipo"),
    [
        ("numero_alterado", "numero_sin_respaldo"),
        ("fecha_alterada", "numero_sin_respaldo"),
        ("entidad_inventada", "entidad_sin_respaldo"),
        ("negacion_invertida", "negacion_perdida"),
        ("garantia_inventada", "compromiso_sin_respaldo"),
        ("spam_convertido_en_logro", "activo_de_mensaje_excluido"),
    ],
)
def test_cada_variante_explica_su_alerta(variante, tipo):
    fila = next(f for f in FILAS if f["ruta"] == variante)
    assert tipo in {a["tipo"] for a in fila["alertas"]}


def test_autor_de_los_metadatos_no_es_entidad_inventada():
    original = "Completé 3 ejercicios de Python en ONE."
    salida = "Ana Prueba completó 3 ejercicios de Python en ONE."
    assert auditar_activo(original, salida, metadatos=("Ana Prueba",)) == []
    assert auditar_activo(original, salida)[0]["tipo"] == "entidad_sin_respaldo"


def test_fuentes_aprobadas_y_palabras_excluidas_son_configurables():
    original = "¿Cómo uso Grid en un dashboard?"
    salida = "En CSS, Grid organiza filas y columnas; es gratis."
    assert auditar_activo(original, salida)[0]["detalle"] == "CSS"
    assert auditar_activo(original, salida, fuentes=["CSS"]) == []
    alertas = auditar_activo(original, salida, fuentes=["CSS"], excluidas=["gratis"])
    assert [a["tipo"] for a in alertas] == ["palabra_excluida"]


def test_numero_en_letras_equivale_a_cifra():
    original = "Construí mi modelo en 6 semanas."
    assert auditar_activo(original, "Construyó su modelo en seis semanas.") == []
    assert auditar_activo(original, "Construyó su modelo en ocho semanas.") != []


def test_instruccion_del_prompt_filtrada_en_la_salida():
    original = "¿Cuál es la diferencia entre las rutas de Data Analyst y Data Scientist?"
    salida = ("Una redacción breve que indique que las diferencias deben confirmarse con la "
              "información oficial. No inventes descripciones de planes de estudio.")
    alertas = auditar_activo(original, salida, metadatos=("Carlos Mena",))
    assert [a["tipo"] for a in alertas] == ["instruccion_filtrada"]
    assert "no inventes" in alertas[0]["detalle"]
    assert auditar_activo(original, "Las diferencias deben confirmarse con la información oficial.") == []
    # Si el propio mensaje trae la frase, no es una filtración.
    assert auditar_activo("Por favor no inventes datos.", "Pide que no inventes datos.") == []


@pytest.mark.parametrize(
    ("original", "salida", "detalle"),
    [
        ("El networking que generé en este programa me abrió puertas para colaborar en proyectos open source.",
         "Gabriela Núñez indica que el networking le abrió puertas para colaborar en proyectos open source. "
         "No se especifica el tipo de proyectos ni el alcance de la colaboración.",
         "no se especifica"),
        ("El acompañamiento del mentor fue clave para entender conceptos de machine learning.",
         "Laura Ocampo destaca al mentor. No se menciona ningún logro adicional en el mensaje original.",
         "no se menciona, mensaje original"),
        ("¿El certificado final tiene costo adicional o está incluido en el programa?",
         "El costo debe confirmarse con la información oficial, ya que la pregunta no proporciona ese dato.",
         "ya que la pregunta no proporciona"),
    ],
)
def test_comentario_interno_para_el_revisor(original, salida, detalle):
    alertas = auditar_activo(original, salida, metadatos=("Gabriela Núñez", "Laura Ocampo"))
    assert [(a["tipo"], a["detalle"]) for a in alertas] == [("comentario_interno", detalle)]


def test_redaccion_prudente_no_es_comentario_interno():
    original = "¿Por qué me sale KeyError en Python?"
    salida = "Con la información recibida no se puede confirmar la causa; consulta la documentación oficial."
    assert auditar_activo(original, salida) == []


def test_hashtag_sin_almohadilla():
    entrega = {
        "interacciones": [{"id": "a-1", "autor": "Ana", "canal": "#logros", "texto": "Terminé 2 cursos de Python."}],
        "activos": [{"id_interaccion": "a-1", "tipo": "linkedin",
                     "contenido": {"contenido": "Ana terminó 2 cursos de Python.",
                                   "hashtags": ["#Python", "Aprendizaje", "ModeloDeClasificación"]}}],
    }
    filas = auditar_entrega(entrega, None, SIN_OPCIONES)
    assert filas[0]["alertas"] == [
        {"tipo": "hashtag_sin_almohadilla", "detalle": "Aprendizaje, ModeloDeClasificación"}]


def test_entrega_marca_activos_sin_original_y_de_mensajes_excluidos():
    entrega = {
        "interacciones": [{"id": "a-1", "autor": "Ana", "canal": "#logros", "texto": "Terminé 2 cursos."}],
        "activos": [
            {"id_interaccion": "a-1", "tipo": "boletin", "contenido": {"titular": "Ana terminó 2 cursos"}},
            {"id_interaccion": "a-9", "tipo": "boletin", "contenido": {"titular": "Sin origen"}},
        ],
    }
    informe = {"lotes": [{"evaluaciones": [{"id": "a-1", "motivos": ["texto_repetitivo"]}]}]}
    filas = auditar_entrega(entrega, informe, SIN_OPCIONES)
    assert [a["tipo"] for a in filas[0]["alertas"]] == ["activo_de_mensaje_excluido"]
    assert [a["tipo"] for a in filas[1]["alertas"]] == ["sin_original"]


def test_entrega_separa_alertas_por_modelo_y_respaldo():
    entrega = {
        "interacciones": [{"id": "a-1", "autor": "Ana", "canal": "#logros", "texto": "Terminé 2 cursos."}],
        "activos": [
            {"id_interaccion": "a-1", "tipo": "boletin", "contenido": {"titular": "Ana terminó 2 cursos"},
             "proveedor": "nvidia", "modelo": "llama-8b", "uso_fallback": False},
            {"id_interaccion": "a-1", "tipo": "linkedin", "contenido": {"texto": "Ana terminó 5 cursos"},
             "proveedor": "gemini", "modelo": "flash", "uso_fallback": True},
        ],
    }
    filas = auditar_entrega(entrega, None, SIN_OPCIONES)
    assert [f["uso_fallback"] for f in filas] == [False, True]
    assert resumen(filas)["por_modelo"] == {
        "gemini/flash (fallback)": {"activos": 1, "con_alertas": 1},
        "nvidia/llama-8b": {"activos": 1, "con_alertas": 0},
    }
    assert "gemini/flash (fallback)" in a_markdown({
        "metadatos": {"proveedor": "por_activo", "version_codigo": "f242934", "modo": "entrega"},
        "resumen": resumen(filas), "filas": filas})


@pytest.mark.parametrize("motivo", ["bajo_umbral", "texto_corto", "fuera_maximo_por_lote"])
def test_no_confunde_seleccion_de_contenido_con_exclusion_de_ia(motivo):
    entrega = {
        "interacciones": [{"id": "a-1", "texto": "Terminé 2 cursos."}],
        "activos": [{"id_interaccion": "a-1", "tipo": "boletin",
                     "contenido": "Terminó 2 cursos."}],
    }
    informe = {"lotes": [{"evaluaciones": [{
        "id": "a-1", "motivos": [motivo], "incluido_sentimiento": True,
        "motivos_exclusion_sentimiento": [],
    }]}]}
    # La elegibilidad de una ruta se comprueba aparte: este mensaje no es ruido.
    assert auditar_entrega(entrega, informe, SIN_OPCIONES)[0]["alertas"] == []


@pytest.mark.parametrize("con_campos_actuales", [True, False])
def test_mantiene_exclusion_por_ruido_en_informes_actuales_y_anteriores(con_campos_actuales):
    evaluacion = {"id": "a-1", "motivos": ["texto_repetitivo", "bajo_umbral"]}
    if con_campos_actuales:
        evaluacion.update(incluido_sentimiento=False,
                          motivos_exclusion_sentimiento=["texto_repetitivo"])
    entrega = {
        "interacciones": [{"id": "a-1", "texto": "compra ahora compra ahora"}],
        "activos": [{"id_interaccion": "a-1", "tipo": "boletin", "contenido": "Gran logro."}],
    }
    informe = {"lotes": [{"evaluaciones": [evaluacion]}]}
    assert auditar_entrega(entrega, informe, SIN_OPCIONES)[0]["alertas"] == [{
        "tipo": "activo_de_mensaje_excluido",
        "detalle": "el mensaje se excluyó antes de la IA (texto_repetitivo)",
    }]


def test_exclusion_explicita_sin_motivo_no_se_pierde():
    entrega = {
        "interacciones": [{"id": "a-1", "texto": "Mensaje excluido."}],
        "activos": [{"id_interaccion": "a-1", "tipo": "boletin", "contenido": "Mensaje excluido."}],
    }
    informe = {"lotes": [{"evaluaciones": [{
        "id": "a-1", "motivos": [], "incluido_sentimiento": False,
    }]}]}
    assert auditar_entrega(entrega, informe, SIN_OPCIONES)[0]["alertas"][0]["tipo"] == "activo_de_mensaje_excluido"


def test_compatibilidad_de_exclusiones_anteriores_con_el_contrato_de_da():
    from scripts.auditoria_consistencia import MOTIVOS_EXCLUSION_CALIDAD
    from src.datos.relevancia import MOTIVOS_RUIDO

    assert MOTIVOS_EXCLUSION_CALIDAD == MOTIVOS_RUIDO


@pytest.mark.parametrize("anidada", [True, False])
def test_rechaza_ids_duplicados_antes_de_elegir_un_original(anidada):
    if anidada:
        interacciones = [
            {"id": "a-1", "entrada": {"texto": "Completé 2 cursos."}},
            {"id": "a-1", "entrada": {"texto": "Completé 5 cursos."}},
        ]
    else:
        interacciones = [
            {"id": "a-1", "texto": "Completé 2 cursos."},
            {"id": "a-1", "texto": "Completé 5 cursos."},
        ]
    with pytest.raises(ValueError, match="ID duplicado.*a-1"):
        auditar_entrega({"interacciones": interacciones, "activos": []}, None, SIN_OPCIONES)


def test_fuente_tecnica_aprobada_no_oculta_otra_entidad_nueva():
    original = "¿Cómo reviso un error en pandas?"
    salida = "Revisa el DataFrame antes de enviarlo a EmpresaInventada."
    alertas = auditar_activo(original, salida, fuentes=["DataFrame"])
    assert alertas == [{"tipo": "entidad_sin_respaldo", "detalle": "EmpresaInventada"}]


def test_comentario_interno_es_aviso_y_no_rechazo_automatico():
    # Explicación técnica legítima que la heurística no puede distinguir por sí sola.
    original = "¿Cómo funciona un índice?"
    salida = "Si no se especifica un índice, se utiliza el predeterminado."
    entrega = {
        "interacciones": [{"id": "a-1", "texto": original}],
        "activos": [{"id_interaccion": "a-1", "tipo": "preguntas_frecuentes", "contenido": salida}],
    }
    fila = auditar_entrega(entrega, None, SIN_OPCIONES)[0]
    assert fila["alertas"][0]["tipo"] == "comentario_interno"
    assert fila["decision_sugerida"] == "revisar"
    assert fila["decision_humana"] is None


def test_entrega_anidada_de_ds_se_aplana_con_trazabilidad():
    def traza(modelo, fallback=False):
        return {"proveedor_usado": "gemini" if fallback else "nvidia_nim", "modelo": modelo,
                "fallback_activado": fallback, "tier": "rapido"}

    entrega = {
        "version_auditoria": "1.2",
        "interacciones": [
            {"id": "int-001",
             "entrada": {"autor": "Camila Restrepo", "canal": "#logros-y-empleos",
                         "texto": "Conseguí mi primer trabajo como analista de datos en menos de 3 meses."},
             "datos": {"excluido_por_data": False, "motivos_exclusion": []},
             "activos": {
                 "boletin": {"contenido": {"titular": "Camila consigue trabajo en menos de 3 meses"},
                             "trazabilidad": traza("nemotron-30b")},
                 "linkedin": {"contenido": {"contenido": "Camila consiguió trabajo en 2 meses"},
                              "trazabilidad": traza("flash-lite", fallback=True)},
             }},
            {"id": "int-099",
             "entrada": {"autor": "Bot", "canal": "#general", "texto": "promo promo promo"},
             "datos": {"excluido_por_data": True, "motivos_exclusion": ["texto_repetitivo"]},
             "activos": {"boletin": {"contenido": {"titular": "Gran logro"}, "trazabilidad": traza("nemotron-30b")}}},
        ],
    }
    filas = auditar_entrega(entrega, None, SIN_OPCIONES)
    assert [(f["id_interaccion"], f["ruta"]) for f in filas] == [
        ("int-001", "boletin"), ("int-001", "linkedin"), ("int-099", "boletin")]
    assert filas[0]["alertas"] == []
    assert "numero_sin_respaldo" in {a["tipo"] for a in filas[1]["alertas"]}
    assert "activo_de_mensaje_excluido" in {a["tipo"] for a in filas[2]["alertas"]}
    assert resumen(filas)["por_modelo"] == {
        "gemini/flash-lite (fallback)": {"activos": 1, "con_alertas": 1},
        "nvidia_nim/nemotron-30b": {"activos": 2, "con_alertas": 1},
    }


def test_cli_escribe_json_y_markdown(tmp_path, capsys):
    salida_json, salida_md = tmp_path / "reporte.json", tmp_path / "reporte.md"
    assert principal(["--casos", str(FIXTURE), "--salida-json", str(salida_json), "--salida-md", str(salida_md)]) == 0
    reporte = json.loads(salida_json.read_text(encoding="utf-8"))
    assert reporte["resumen"]["coinciden_con_lo_esperado"] == reporte["resumen"]["con_decision_esperada"] == 12
    assert "| Decisión humana |" in salida_md.read_text(encoding="utf-8")
    assert '"activos": 12' in capsys.readouterr().out
