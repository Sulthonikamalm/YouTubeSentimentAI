"""Quick test: measure Ollama response time with NEW lightweight prompt."""
import time, sys, os
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv()

import requests
from backend.ml.ollama_service import build_prompt, get_ollama_settings, _parse_label_response

cfg = get_ollama_settings()
print(f"=== Ollama Config ===")
print(f"  Model:   {cfg['model']}")
print(f"  URL:     {cfg['base_url']}")
print(f"  Timeout: {cfg['timeout']}s")

# Test: Real analysis prompt with single comments
print("\n=== Test: Real analysis prompt (single comments sequential) ===")
test_comments = [
    {"comment_id": "t1", "comment_text": "Pemerintah gagal, harga beras mahal"},
    {"comment_id": "t2", "comment_text": "Video bagus, terima kasih sudah menjelaskan"},
    {"comment_id": "t3", "comment_text": "Korupsi merajalela, kapan bersih"},
]

for item in test_comments:
    cid = item["comment_id"]
    text = item["comment_text"]
    prompt = build_prompt(text)
    print(f"\n  Sending comment [{cid}] to Ollama...: \"{text}\"")
    t0 = time.time()
    r = requests.post(f"{cfg['base_url']}/api/generate", json={
        "model": cfg["model"],
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 150}
    }, timeout=cfg["timeout"])
    elapsed = time.time() - t0
    
    if r.status_code == 200:
        data = r.json()
        resp_text = data.get("response", "")
        print(f"  Response received in {elapsed:.1f}s:")
        print(f"  {resp_text.strip()}")
        
        parsed = _parse_label_response(resp_text)
        print(f"  Parsed JSON:")
        print(f"    {parsed}")
    else:
        print(f"  HTTP Error {r.status_code}: {r.text}")

print(f"\n=== DONE ===")
