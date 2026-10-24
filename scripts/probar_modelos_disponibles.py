import os
import requests
import dotenv

dotenv.load_dotenv()
key = os.getenv("NVIDIA_API_KEY")
headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

# Query /v1/models
r = requests.get("https://integrate.api.nvidia.com/v1/models", headers=headers)
all_models = [m["id"] for m in r.json().get("data", [])]

# Filter out embed, reward, guard, parse, etc.
chat_candidates = [
    m for m in all_models
    if not any(x in m.lower() for x in [
        "embed", "guard", "reward", "parse", "clip", "synthetic",
        "deplot", "fuyu", "kosmos", "neva", "calibration", "vila"
    ])
]

print(f"Testing {len(chat_candidates)} candidate models...")
accessible = []

for m in sorted(chat_candidates):
    payload = {
        "model": m,
        "messages": [{"role": "user", "content": 'Responde {"ok": true}'}],
        "max_tokens": 15,
        "temperature": 0,
    }
    try:
        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=8,
        )
        if resp.status_code == 200:
            print(f"[ACCESSIBLE] {m}")
            accessible.append(m)
        else:
            print(f"[{resp.status_code}] {m}")
    except Exception as e:
        print(f"[TIMEOUT/ERR] {m}: {e}")

print(f"\nTotal accessible: {len(accessible)}")
with open("salida/experimentos/modelos_nvidia_accesibles.json", "w", encoding="utf-8") as f:
    import json
    json.dump(accessible, f, indent=4)
