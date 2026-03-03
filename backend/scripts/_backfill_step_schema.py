"""Backfill file_schema and ap_schema on existing StepFile nodes.

Reads the actual .stp files from data/uploads/ and re-parses metadata
to populate the file_schema and ap_schema fields that were missed due
to a regex bug (now fixed).
"""
import os, sys, pathlib

backend = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend))

# Load .env
env_file = backend.parent / ".env"
if env_file.is_file():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        if k.strip() not in os.environ:
            os.environ[k.strip()] = v.strip()

from src.web.services.neo4j_service import get_neo4j_service
from src.parsers.step_parser import parse_step_metadata

neo = get_neo4j_service()
uploads_dir = backend.parent / "data" / "uploads"

# Get all StepFile nodes
step_files = neo.execute_query(
    "MATCH (f:StepFile) RETURN f.uri AS uri, f.name AS name, f.file_schema AS fs, f.ap_schema AS ap",
    {},
)

print(f"Found {len(step_files)} StepFile nodes")
updated = 0
skipped = 0

for sf in step_files:
    uri = sf["uri"]
    name = sf["name"]

    # Already has schema
    if sf.get("fs"):
        skipped += 1
        continue

    # Try to find the file
    fpath = pathlib.Path(uri)
    if not fpath.exists():
        # Try data/uploads
        fpath = uploads_dir / name
        if not fpath.exists():
            print(f"  SKIP (file not found): {name}")
            skipped += 1
            continue

    meta = parse_step_metadata(fpath)
    if not meta.file_schema:
        print(f"  SKIP (no FILE_SCHEMA in file): {name}")
        skipped += 1
        continue

    # Detect AP level
    ap_schema = None
    ap_level = None
    upper = meta.file_schema.upper()
    if "AP242" in upper:
        ap_schema = "AP242"
        ap_level = "AP242"
    elif "AP239" in upper:
        ap_schema = "AP239"
        ap_level = "AP239"
    elif "AP243" in upper:
        ap_schema = "AP243"
        ap_level = "AP243"

    # Update
    neo.execute_write(
        """
        MATCH (f:StepFile {uri: $uri})
        SET f.file_schema = $file_schema,
            f.file_name = $file_name,
            f.ap_schema = $ap_schema,
            f.ap_level = $ap_level,
            f.updated_on = datetime()
        """,
        {
            "uri": uri,
            "file_schema": meta.file_schema,
            "file_name": meta.file_name,
            "ap_schema": ap_schema,
            "ap_level": ap_level,
        },
    )
    print(f"  UPDATED: {name} -> schema={meta.file_schema}, AP={ap_schema}")
    updated += 1

# Also propagate ap_level to StepInstance nodes that belong to these files
if updated > 0:
    print(f"\nPropagating ap_level to StepInstance nodes...")
    result = neo.execute_write(
        """
        MATCH (f:StepFile)-[:CONTAINS]->(i:StepInstance)
        WHERE f.ap_level IS NOT NULL AND i.ap_level IS NULL
        SET i.ap_level = f.ap_level
        RETURN count(i) AS cnt
        """,
        {},
    )
    cnt = result[0]["cnt"] if result else 0
    print(f"  Updated {cnt:,} StepInstance nodes with ap_level")

print(f"\nDone: {updated} updated, {skipped} skipped")
