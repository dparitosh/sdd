#!/usr/bin/env python3
"""
SDD v4.0 Schema Migration Runner.

Connects to Neo4j via ``core.database`` and executes both migration files:
  1. ``migrate_schema_v4.cypher``   — constraints, indexes, Standard nodes
  2. ``migrate_digital_thread.cypher`` — digital thread relationships + VV_Plan/ProductSpec

Usage:
    cd backend
    python scripts/run_migration_v4.py

Environment:
    Requires NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD (via .env or env vars).
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# ---------------------------------------------------------------------------
# Path setup — ensure ``import src...`` works
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
for _p in (str(BACKEND_ROOT), str(BACKEND_ROOT / "src")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

load_dotenv(REPO_ROOT / ".env")

from src.core.database import get_driver


# ---------------------------------------------------------------------------
# Cypher execution helpers
# ---------------------------------------------------------------------------

def _strip_comments(statement: str) -> str:
    """Remove ``//`` comment lines from a Cypher statement."""
    return "\n".join(
        line for line in statement.split("\n")
        if not line.strip().startswith("//")
    ).strip()


def _execute_cypher_file(driver, file_path: Path) -> tuple[int, int]:
    """Run every Cypher statement in *file_path* and return (ok, failed) counts."""
    logger.info(f"Loading {file_path.name}  ({file_path})")

    text = file_path.read_text(encoding="utf-8")

    # Split on semicolons to get individual statements
    raw_statements = [s.strip() for s in text.split(";") if s.strip()]

    # Filter out blocks that are only comments or blank
    statements = []
    for stmt in raw_statements:
        cleaned = _strip_comments(stmt)
        if cleaned:
            statements.append(cleaned)

    logger.info(f"  {len(statements)} executable statement(s) found")

    ok = 0
    failed = 0

    for idx, stmt in enumerate(statements, 1):
        first_line = stmt.split("\n")[0][:72]
        try:
            records, summary, _ = driver.execute_query(stmt)
            ok += 1

            # Log counters from the summary when available
            counters = summary.counters if summary else None
            if counters:
                parts = []
                if counters.nodes_created:
                    parts.append(f"{counters.nodes_created} nodes created")
                if counters.relationships_created:
                    parts.append(f"{counters.relationships_created} rels created")
                if counters.constraints_added:
                    parts.append(f"{counters.constraints_added} constraints added")
                if counters.indexes_added:
                    parts.append(f"{counters.indexes_added} indexes added")
                if counters.properties_set:
                    parts.append(f"{counters.properties_set} props set")
                extra = (" — " + ", ".join(parts)) if parts else ""
            else:
                extra = ""

            # Log returned rows for SHOW / RETURN queries
            if records:
                extra += f" — {len(records)} row(s) returned"

            logger.info(f"  [{idx}/{len(statements)}] OK: {first_line}{extra}")

        except Exception as exc:
            failed += 1
            logger.error(f"  [{idx}/{len(statements)}] FAIL: {first_line}")
            logger.error(f"    {type(exc).__name__}: {exc}")

    return ok, failed


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    scripts_dir = BACKEND_ROOT / "scripts"
    files = [
        scripts_dir / "migrate_schema_v4.cypher",
        scripts_dir / "migrate_digital_thread.cypher",
    ]

    for f in files:
        if not f.exists():
            logger.error(f"Migration file not found: {f}")
            return 1

    logger.info("=" * 72)
    logger.info("SDD v4.0 Schema Migration")
    logger.info("=" * 72)

    start = time.time()

    try:
        driver = get_driver()
    except Exception as exc:
        logger.error(f"Cannot connect to Neo4j: {exc}")
        return 1

    total_ok = 0
    total_fail = 0

    for f in files:
        logger.info("-" * 72)
        ok, fail = _execute_cypher_file(driver, f)
        total_ok += ok
        total_fail += fail

    elapsed = time.time() - start

    logger.info("=" * 72)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 72)
    logger.info(f"  Statements OK   : {total_ok}")
    logger.info(f"  Statements FAIL : {total_fail}")
    logger.info(f"  Elapsed         : {elapsed:.1f}s")
    logger.info("=" * 72)

    if total_fail:
        logger.warning(f"{total_fail} statement(s) failed — review logs above.")
        return 1

    logger.success("✓ Migration completed successfully!")

    # Quick verification
    logger.info("\n--- Verification ---")
    try:
        rows, _, _ = driver.execute_query("SHOW CONSTRAINTS YIELD name RETURN name ORDER BY name")
        logger.info(f"Constraints: {len(rows)}")
        for r in rows:
            logger.info(f"  • {r['name']}")

        rows, _, _ = driver.execute_query("SHOW INDEXES YIELD name RETURN name ORDER BY name")
        logger.info(f"Indexes: {len(rows)}")
        for r in rows:
            logger.info(f"  • {r['name']}")

        rows, _, _ = driver.execute_query("MATCH (s:Standard) RETURN s.name AS name ORDER BY name")
        logger.info(f"Standard nodes: {len(rows)}")
        for r in rows:
            logger.info(f"  • {r['name']}")
    except Exception as exc:
        logger.warning(f"Verification queries failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
