import os
import json
import time
import dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from pydantic import ValidationError

from src.agentes.modelos import AnalisisLote
from src.agentes.prompts.analisis import template_analisis_lote
from src.agentes.proveedores.nvidia_nim import _agregar_instruccion_esquema

dotenv.load_dotenv()
api_key = os.getenv("NVIDIA_API_KEY")

with open("salida/experimentos/holdout_texto_corregido_fixture_v1.json", "r", encoding="utf-8") as f:
    fixture = json.load(f)

# Take first batch of 10 cases
casos = fixture["casos"][:10]
mensajes = [
    {
        "id": c["id"],
        "origen": c["origen"],
        "canal": c["canal"],
        "idioma": c["idioma"],
        "texto": c["texto"],
    }
    for c in casos
]

prompt = template_analisis_lote.invoke({"mensajes_json": json.dumps(mensajes, ensure_ascii=False)})
preparado = _agregar_instruccion_esquema(prompt, AnalisisLote)

candidates = [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "meta/llama-3.2-90b-vision-instruct",
    "meta/llama-3.2-11b-vision-instruct",
    "google/gemma-4-31b-it",
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "z-ai/glm-5.3",
    "z-ai/glm-5.3-flash",
    "moonshotai/kimi-k3",
    "openai/gpt-oss-20b",
]

print(f"Testing {len(candidates)} candidates on 10 holdout cases...\n", flush=True)

for model in candidates:
    print(f"=== Model: {model} ===", flush=True)
    for with_thinking_flag in [True, False]:
        extra = {"chat_template_kwargs": {"enable_thinking": False}} if with_thinking_flag else {}
        t0 = time.time()
        try:
            client = ChatOpenAI(
                api_key=api_key,
                base_url="https://integrate.api.nvidia.com/v1",
                model=model,
                temperature=0,
                timeout=45,
                max_retries=0,
                extra_body=extra,
            ).bind(response_format={"type": "json_object"})
            
            resp = client.invoke(preparado)
            elapsed = round(time.time() - t0, 2)
            parsed = AnalisisLote.model_validate_json(resp.content)
            ids_received = {r.id for r in parsed.resultados}
            expected_ids = {c["id"] for c in casos}
            missing = expected_ids - ids_received
            print(f"  [OK] with_thinking_flag={with_thinking_flag}: {elapsed}s, parsed {len(parsed.resultados)} items, missing {len(missing)}", flush=True)
            break
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"  [FAIL] with_thinking_flag={with_thinking_flag}: {elapsed}s, Error: {type(e).__name__}: {str(e)[:120]}", flush=True)
