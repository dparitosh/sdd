from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(12):
        if (cur / "backend").is_dir() and (cur / "package.json").exists():
            return cur
        if (cur / "backend").is_dir() and (cur / "README.md").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError(f"Could not find repo root from: {start}")


REPO_ROOT = _find_repo_root(Path(__file__))


# Scripts that must support `--help` without connecting to external services.
# Keep this list small and move scripts over as they are refactored.
SAFE_HELP_SCRIPTS: list[str] = [
    "backend/scripts/check_kg.py",
    "backend/scripts/check_kg_status.py",
    "backend/scripts/check_semantic_kg.py",
    "backend/scripts/check_entity_properties.py",
    "backend/scripts/list_schemas.py",
    "backend/scripts/clear_db.py",
    "backend/scripts/fix_comment_newlines.py",
    "backend/scripts/ingest_ontology_rdf.py",
    "backend/scripts/ingest_step_file.py",
    "backend/scripts/ingest_step_folder.py",
    "backend/scripts/neo4j_schema_audit_quick.py",
    "backend/scripts/reload_database.py",

    # Ingesters / orchestrators: smoke-test only `--help` (no ingestion is run).
    "backend/scripts/ingest_schemas.py",
    "backend/scripts/ingest_semantic_layer.py",
    "backend/scripts/ingest_xmi.py",
    "backend/scripts/ingest_xmi_v2.py",
    "backend/scripts/ingest_xsd.py",
    "backend/scripts/ingest_xsd_v2.py",
    "backend/scripts/link_ap_hierarchy.py",
]


# Scripts intentionally skipped from `--help` smoke testing for now.
# Every script in backend/scripts must appear either here or in SAFE_HELP_SCRIPTS.
SKIPPED_SCRIPTS: dict[str, str] = {
    # Non-CLI / special-purpose scripts.
    "backend/scripts/create_sample_data.py": "Integration script; does not provide a stable CLI yet.",
    "backend/scripts/run_migration.py": "Integration script; does not provide a stable CLI yet.",

    # HTTP-based scripts (require backend server to be running and are not argparse CLIs).
    "backend/scripts/test_rest_api.py": "Requires running API server; not a CLI.",
    "backend/scripts/validate_api_alignment.py": "Requires running API server; not a CLI.",
}


def _all_backend_script_relpaths() -> list[str]:
    scripts_dir = REPO_ROOT / "backend" / "scripts"
    paths = []
    for p in sorted(scripts_dir.glob("*.py")):
        paths.append(str(p.relative_to(REPO_ROOT)).replace("\\", "/"))
    return paths


def _run_help(script_relpath: str) -> subprocess.CompletedProcess[str]:
    script_path = REPO_ROOT / Path(script_relpath)

    env = os.environ.copy()
    # Ensure script output is predictable and avoids encoding issues on Windows.
    env.setdefault("PYTHONIOENCODING", "utf-8")

    return subprocess.run(
        [sys.executable, str(script_path), "--help"],
        cwd=str(REPO_ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=20,
    )


@pytest.mark.parametrize("script_relpath", SAFE_HELP_SCRIPTS)
def test_scripts_support_help_without_traceback(script_relpath: str) -> None:
    proc = _run_help(script_relpath)

    # argparse should exit with 0 on --help.
    assert proc.returncode == 0, (
        f"{script_relpath} returned {proc.returncode}\n"
        f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
    )

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    assert "Traceback (most recent call last)" not in combined


def test_all_backend_scripts_are_categorized() -> None:
    all_scripts = set(_all_backend_script_relpaths())
    safe = set(SAFE_HELP_SCRIPTS)
    skipped = set(SKIPPED_SCRIPTS.keys())

    uncategorized = sorted(all_scripts - safe - skipped)
    assert not uncategorized, (
        "Uncategorized backend/scripts/*.py files found. "
        "Add them to SAFE_HELP_SCRIPTS or SKIPPED_SCRIPTS with a reason:\n"
        + "\n".join(uncategorized)
    )


@pytest.mark.parametrize("script_relpath", sorted(SKIPPED_SCRIPTS.keys()))
def test_skipped_scripts_have_reasons(script_relpath: str) -> None:
    reason = SKIPPED_SCRIPTS.get(script_relpath)
    assert reason and reason.strip(), f"Missing skip reason for {script_relpath}"
