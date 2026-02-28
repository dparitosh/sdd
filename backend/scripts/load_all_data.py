#!/usr/bin/env python3
"""
Master Data Load Script -- Full Knowledge Graph Ingestion Pipeline
==========================================================================
Runs all ingestion steps in correct dependency order to build a complete,
connected Neo4j graph from scratch.

Pipeline sequence
-----------------
  1.  XMI + Clear DB    reload_database.py --yes
                        Loads Domain_model.xmi via SemanticXMILoader
                        (creates all structural UML/SysML nodes + relationships)

  2.  SDD schema        run_sdd_schema_migration.py
                        Constraints, indexes, REQ-01→REQ-V1 stub requirements

  3.  AP hierarchy      run_migration.py
                        migrate_to_ap_hierarchy.cypher  -- AP-level metadata

  4.  AP sample nodes   migrations/002_ap_hierarchy_sample_data.py  (inline)
                        Creates typed AP239/AP242/AP243 sample nodes

  5.  SDD data          ingest_sdd_data.py
                        SimulationDossier, SimulationRun, SimulationArtifact,
                        EvidenceCategory, KPI nodes + MoSSEC links

  6.  Sample data       create_sample_data.py
                        Requirements, traceability, constraints, DataTypes

  7.  AP links          link_ap_hierarchy.py
                        Cross-level semantic relationships (AP239↔AP242↔AP243)

  8.  Digital thread v4 run_migration_v4.py
                        migrate_schema_v4.cypher + migrate_digital_thread.cypher
                        Creates 11 digital-thread relationship types

  9.  OWL ontologies    ingest_ontology_rdf.py  (per OWL file)
                        MoSSEC AP243, STEP Core, Product Life Cycle Support

  10. OSLC seed         python -m backend.scripts.load_oslc_seed
                        OSLC Core, RM, AP242, AP243 vocabularies as OntologyClass

Usage
-----
    # Normal run (from repo root)
    python backend/scripts/load_all_data.py

    # Dry-run (validate environment & file paths without connecting)
    python backend/scripts/load_all_data.py --dry-run

    # Skip specific steps (comma-separated step numbers: 1,2,...)
    python backend/scripts/load_all_data.py --skip 9,10

    # Only run specific steps
    python backend/scripts/load_all_data.py --only 1,5,6,7,8

Notes
-----
* Step 1 is DESTRUCTIVE (DETACH DELETE all nodes).  The script refuses to run
  step 1 without --yes or interactive confirmation.
* All steps use MERGE, so it is safe to re-run steps 2-10 independently.
* Set LOAD_ALL_VERBOSE=1 in environment to see full stdout of each step.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT   = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
SCRIPTS     = BACKEND_ROOT / "scripts"
PYTHON      = sys.executable

# -- colour helpers ----------------------------------------------------------
_USE_COLOUR = sys.stdout.isatty()
def _c(code, text): return f"\033[{code}m{text}\033[0m" if _USE_COLOUR else text
OK   = lambda t: _c("32;1", t)
WARN = lambda t: _c("33;1", t)
ERR  = lambda t: _c("31;1", t)
HDR  = lambda t: _c("36;1", t)
DIM  = lambda t: _c("2",    t)


def _sep(label: str = ""):
    width = 72
    if label:
        pad = (width - len(label) - 2) // 2
        print(f"\n{'-' * pad} {HDR(label)} {'-' * pad}")
    else:
        print("-" * width)


def _run(label: str, cmd: list[str | Path], *, cwd=REPO_ROOT,
         skip=False, dry_run=False, fatal=True) -> bool:
    """Run a subprocess step; return True on success."""
    _sep(label)
    cmd_str = " ".join(str(c) for c in cmd)
    print(DIM(f"  cmd: {cmd_str}"))
    if skip:
        print(WARN("  → SKIPPED"))
        return True
    if dry_run:
        print(WARN("  → DRY RUN (not executed)"))
        return True

    verbose = os.environ.get("LOAD_ALL_VERBOSE", "").strip() in ("1", "true", "yes")
    start = time.perf_counter()
    result = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=not verbose,
        text=True,
    )
    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        print(ERR(f"  ✗ FAILED (exit {result.returncode}) after {elapsed:.1f}s"))
        if not verbose and result.stdout:
            print(DIM("  --- stdout ---"))
            print(result.stdout[-3000:])  # last 3 KB
        if not verbose and result.stderr:
            print(ERR("  --- stderr ---"))
            print(result.stderr[-2000:])
        if fatal:
            sys.exit(result.returncode)
        return False

    print(OK(f"  ✓ done ({elapsed:.1f}s)"))
    return True


def _validate_env() -> bool:
    """Check that critical environment variables and files exist."""
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")

    ok = True
    for var in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        val = os.environ.get(var)
        if not val:
            print(ERR(f"  Missing env var: {var}"))
            ok = False
        else:
            print(OK(f"  {var} = {val[:20]}…"))

    xmi = BACKEND_ROOT / "data" / "raw" / "Domain_model.xmi"
    if not xmi.exists():
        print(ERR(f"  XMI file not found: {xmi}"))
        ok = False
    else:
        print(OK(f"  XMI file: {xmi.name}  ({xmi.stat().st_size // 1024} KB)"))

    return ok


def _migration_002_inline():
    """Run migration 002 (AP hierarchy sample nodes) directly in-process."""
    from dotenv import load_dotenv
    load_dotenv(REPO_ROOT / ".env")

    sys.path.insert(0, str(BACKEND_ROOT))
    from src.graph.connection import Neo4jConnection  # type: ignore
    from src.utils.config import Config               # type: ignore

    cfg  = Config()
    conn = Neo4jConnection(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
    conn.connect()
    try:
        # Import and run migration function directly
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "migration_002",
            SCRIPTS / "migrations" / "002_ap_hierarchy_sample_data.py",
        )
        mod = importlib.util.module_from_spec(spec)  # type: ignore
        spec.loader.exec_module(mod)               # type: ignore
        mod.up(conn)
        print(OK("  In-process migration 002 complete"))
    finally:
        conn.close()


def _print_final_stats():
    """Print node/rel counts after all ingestion steps."""
    try:
        from dotenv import load_dotenv
        load_dotenv(REPO_ROOT / ".env")
        sys.path.insert(0, str(BACKEND_ROOT))
        from src.graph.connection import Neo4jConnection  # type: ignore
        from src.utils.config import Config               # type: ignore

        cfg  = Config()
        conn = Neo4jConnection(cfg.neo4j_uri, cfg.neo4j_user, cfg.neo4j_password)
        conn.connect()

        n = conn.execute_query("MATCH (n) RETURN count(n) AS c")[0]["c"]
        r = conn.execute_query("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
        print(OK(f"  Total nodes       : {n:,}"))
        print(OK(f"  Total relationships: {r:,}"))

        # Pair connectivity test
        WC = ("NOT 'Documentation' IN labels(n) AND NOT 'Comment' IN labels(n)"
              " AND NOT 'DomainConcept' IN labels(n)"
              " AND NOT 'OWLObjectProperty' IN labels(n)"
              " AND NOT 'OWLDatatypeProperty' IN labels(n)")
        wc_m = WC.replace("labels(n)", "labels(m)")
        pairs = conn.execute_query(
            f"MATCH (n)-[r]->(m) WHERE {WC} AND {wc_m} RETURN count(*) AS c"
        )[0]["c"]
        print(OK(f"  Visualisable pairs : {pairs:,}"))

        # Per-label counts (top 15, excluding huge noise labels)
        labels = conn.execute_query(
            "MATCH (n) UNWIND labels(n) AS l"
            " WHERE NOT l IN ['MBSEElement','XSDNode','XSDElement']"
            " RETURN l AS label, count(*) AS c ORDER BY c DESC LIMIT 15"
        )
        print("\n  Key node types:")
        for lab in labels:
            print(f"    {lab['label']:<30} {lab['c']:>6}")

        conn.close()
    except Exception as exc:
        print(WARN(f"  Stats unavailable: {exc}"))


# -- OWL ontologies to ingest (path relative to REPO_ROOT) ------------------
OWL_FILES = [
    # MoSSEC AP243 ontology -- primary simulation domain model
    ("AP243-MoSSEC",  "smrlv12/data/domain_models/mossec/ap243_v1.owl"),
    # STEP Core v4 -- foundational ISO 10303 concepts
    ("STEP-Core-v4",  "smrlv12/data/core_model/core_v4.owl"),
    # Product Life Cycle Support (4439 extended reference data)
    ("PLCS-4439",     "smrlv12/data/domain_models/product_life_cycle_support/4439_rd_v2.owl"),
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Full KG ingestion pipeline -- sequentially runs all steps.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--yes", "-y", action="store_true",
        help="Confirm destructive step 1 (database clear) without interactive prompt."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be run without executing anything."
    )
    parser.add_argument(
        "--skip", default="",
        help="Comma-separated step numbers to skip (e.g. --skip 9,10)."
    )
    parser.add_argument(
        "--only", default="",
        help="Comma-separated step numbers to run exclusively."
    )
    parser.add_argument(
        "--no-fatal", action="store_true",
        help="Continue on non-zero exit codes instead of stopping."
    )
    args = parser.parse_args()

    skip_steps = {int(s) for s in args.skip.split(",") if s.strip()}
    only_steps = {int(s) for s in args.only.split(",") if s.strip()}
    fatal      = not args.no_fatal
    dry_run    = args.dry_run

    def _should_run(n: int) -> bool:
        if only_steps and n not in only_steps:
            return False
        return n not in skip_steps

    print(HDR("\n+==========================================================+"))
    print(HDR("|        SDD / MBSEsmrl -- Full KG Ingestion Pipeline       |"))
    print(HDR("+==========================================================+"))

    _sep("Environment validation")
    if not _validate_env() and not dry_run:
        print(ERR("  Environment check failed. Fix the issues above and retry."))
        return 1

    # -- Step 1: Clear DB + load XMI -----------------------------------------
    if _should_run(1):
        if not dry_run and not args.yes:
            ans = input(WARN(
                "\n  ⚠  Step 1 will DELETE ALL nodes in the database.\n"
                "     Type 'yes' to proceed: "
            ))
            if ans.strip().lower() != "yes":
                print(ERR("  Aborted by user."))
                return 2
        _run(
            "Step 1 · XMI load (clears DB)",
            [PYTHON, SCRIPTS / "reload_database.py", "--yes"],
            dry_run=dry_run, fatal=fatal,
        )

    # -- Step 2: SDD schema (constraints, indexes, REQ stubs) ----------------
    if _should_run(2):
        _run(
            "Step 2 · SDD schema migration",
            [PYTHON, SCRIPTS / "run_sdd_schema_migration.py"],
            dry_run=dry_run, fatal=fatal,
        )

    # -- Step 3: AP hierarchy Cypher migration -------------------------------
    if _should_run(3):
        _run(
            "Step 3 · AP hierarchy (migrate_to_ap_hierarchy.cypher)",
            [PYTHON, SCRIPTS / "run_migration.py"],
            dry_run=dry_run, fatal=fatal,
        )

    # -- Step 4: AP hierarchy sample nodes (migration 001 + 002) -------------
    if _should_run(4):
        _sep("Step 4 · AP hierarchy sample nodes")
        if dry_run:
            print(WARN("  → DRY RUN (not executed)"))
        else:
            try:
                _migration_002_inline()
            except Exception as exc:
                msg = ERR(f"  migration 002 failed: {exc}")
                print(msg)
                if fatal:
                    raise

    # -- Step 5: SDD simulation data -----------------------------------------
    if _should_run(5):
        _run(
            "Step 5 · SDD data (dossiers, artifacts, evidence, KPIs)",
            [PYTHON, BACKEND_ROOT / "scripts" / "ingest_sdd_data.py"],
            cwd=REPO_ROOT, dry_run=dry_run, fatal=fatal,
        )

    # -- Step 6: General sample data (requirements, traceability) ------------
    if _should_run(6):
        _run(
            "Step 6 · Sample data (requirements, traceability, constraints)",
            [PYTHON, SCRIPTS / "create_sample_data.py"],
            dry_run=dry_run, fatal=fatal,
        )

    # -- Step 7: Cross-level AP hierarchy links -------------------------------
    if _should_run(7):
        _run(
            "Step 7 · AP hierarchy links (cross-level semantic relationships)",
            [PYTHON, SCRIPTS / "link_ap_hierarchy.py"],
            dry_run=dry_run, fatal=fatal,
        )

    # -- Step 8: Digital thread v4 migration ---------------------------------
    if _should_run(8):
        _run(
            "Step 8 · Digital thread v4 (migrate_schema_v4 + migrate_digital_thread)",
            [PYTHON, SCRIPTS / "run_migration_v4.py"],
            cwd=BACKEND_ROOT, dry_run=dry_run, fatal=fatal,
        )

    # -- Step 9: OWL ontologies -----------------------------------------------
    if _should_run(9):
        for owl_name, owl_path in OWL_FILES:
            full_path = REPO_ROOT / owl_path
            if not full_path.exists():
                print(WARN(f"  Skipping {owl_name}: file not found ({owl_path})"))
                continue
            _run(
                f"Step 9 · OWL -- {owl_name}",
                [
                    PYTHON, SCRIPTS / "ingest_ontology_rdf.py",
                    "--path", str(full_path),
                    "--name", owl_name,
                ],
                dry_run=dry_run, fatal=False,   # non-fatal: OWL ingest can fail on corrupt files
            )

    # -- Step 10: OSLC vocabulary seed ---------------------------------------
    if _should_run(10):
        _run(
            "Step 10 · OSLC vocabulary seed (oslc-core, oslc-rm, oslc-ap242, oslc-ap243)",
            [PYTHON, "-m", "backend.scripts.load_oslc_seed"],
            cwd=REPO_ROOT, dry_run=dry_run, fatal=False,
        )

    # -- Final statistics -----------------------------------------------------
    _sep("Final statistics")
    if not dry_run:
        _print_final_stats()
    else:
        print(DIM("  (dry-run -- no stats available)"))

    print(OK("\n✓ load_all_data.py complete.\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
