"""One-shot script: analyse the 950-node gap — nodes with uuid but no text."""
import os, pathlib, sys

# ── load .env ────────────────────────────────────────────────────────────────
_env = pathlib.Path(__file__).resolve().parents[2] / ".env"
for _line in _env.read_text(encoding="utf-8").splitlines():
    _line = _line.strip()
    if _line and not _line.startswith("#") and "=" in _line:
        k, _, v = _line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "src"))

from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    os.environ["NEO4J_URI"],
    auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
)

with driver.session(database=os.environ.get("NEO4J_DATABASE", "mossec")) as s:
    # --- nodes with NO usable text
    rows = s.run(
        "MATCH (n) WHERE n.uuid IS NOT NULL "
        "  AND (n.name IS NULL OR trim(n.name) = '') "
        "  AND (n.description IS NULL OR trim(n.description) = '') "
        "  AND (n.text IS NULL OR trim(n.text) = '') "
        "RETURN labels(n) AS lbls, count(n) AS cnt ORDER BY cnt DESC"
    ).data()
    total = sum(r["cnt"] for r in rows)
    print(f"\nNodes with uuid but no extractable text: {total}")
    for r in rows[:20]:
        print(f"  {r['lbls']} : {r['cnt']}")

    # --- sample one gap node to see what fields it has
    print("\n--- Sample gap node properties ---")
    sample = s.run(
        "MATCH (n) WHERE n.uuid IS NOT NULL "
        "  AND (n.name IS NULL OR trim(n.name) = '') "
        "  AND (n.description IS NULL OR trim(n.description) = '') "
        "RETURN properties(n) AS props, labels(n) AS lbls LIMIT 3"
    ).data()
    for row in sample:
        keys = list(row["props"].keys())
        print(f"  labels={row['lbls']}  keys={keys}")

driver.close()
print("\nDone.")
