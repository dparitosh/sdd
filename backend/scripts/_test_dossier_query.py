"""Verify _strip_intent recursive stripping + live search test."""
import sys, os
os.chdir(r"d:\SDD_MOSSEC\backend")
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(r"d:\SDD_MOSSEC\.env")

from src.agents.semantic_agent import _strip_intent

cases = [
    ("list of dossiers",             "dossiers"),
    ("Show me list of dossiers",     "dossiers"),
    ("show all Parts",               "Parts"),
    ("find the requirements",        "requirements"),
    ("Show me all the requirements", "requirements"),
    ("display list of artifacts",    "artifacts"),
]

print("=== _strip_intent unit tests ===")
all_ok = True
for query, expected in cases:
    got = _strip_intent(query)
    ok = got.lower() == expected.lower()
    print(f"  {'OK' if ok else 'FAIL'}: '{query}' -> '{got}' (expected '{expected}')")
    all_ok = all_ok and ok
print(f"Result: {'ALL PASS' if all_ok else 'SOME FAILURES'}\n")

import requests
port = None
for p in [5000, 5001]:
    try:
        r = requests.get(f"http://localhost:{p}/api/health", timeout=2)
        if r.ok:
            port = p
            break
    except Exception:
        pass
print(f"Backend port: {port}")

for query in ["list of dossiers", "Show me list of dossiers"]:
    r = requests.post(
        f"http://localhost:{port}/api/agents/semantic/search",
        json={"query": query, "top_k": 5, "expand": False},
        timeout=15,
    )
    data = r.json().get("data", {})
    hits = data.get("hits", [])
    uids = [h.get("uid") for h in hits]
    print(f"  '{query}' -> {len(hits)} hits  type_match={data.get('type_match')}  uids={uids}")

