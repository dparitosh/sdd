#!/usr/bin/env python3
"""Bulk-ingest STEP files from a folder into Neo4j.

Supports:
- .stp/.step (ISO 10303-21 Part 21 clear text)
- .stpx (ISO 10303-28 STEP-XML) best-effort

This is a lightweight ingestion: it stores raw instances and references so you
can query them in Neo4j and then build AP242 mappings on top.

Important:
- This script is designed so `--help` does not connect to Neo4j.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _iter_step_files(root: Path, recursive: bool) -> list[Path]:
    exts = {".stp", ".step", ".stpx"}
    it = root.rglob("*") if recursive else root.glob("*")
    files: list[Path] = []
    for p in it:
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    # Smallest-first helps validate quickly and gives faster feedback.
    files.sort(key=lambda p: (p.stat().st_size, str(p).lower()))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk ingest STEP files from a folder")
    parser.add_argument("--root", required=True, help="Folder containing .stp/.step/.stpx files")
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only scan the immediate folder (no recursion)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of files to ingest",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Neo4j UNWIND batch size (default: 500)",
    )
    args = parser.parse_args()

    # Import only after argparse has handled `--help`.
    from dotenv import load_dotenv
    from loguru import logger

    from src.web.services.step_ingest_service import (  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
        StepIngestConfig,
        StepIngestService,
    )

    load_dotenv()

    root = Path(args.root).resolve()
    if not root.exists() or not root.is_dir():
        raise SystemExit(f"Root folder does not exist or is not a directory: {root}")

    files = _iter_step_files(root, recursive=not args.no_recursive)
    if args.limit is not None:
        files = files[: max(0, int(args.limit))]

    logger.info(f"Discovered {len(files)} STEP files under: {root}")
    if not files:
        return 0

    svc = StepIngestService(StepIngestConfig(batch_size=args.batch_size))

    ok = 0
    failed = 0
    total_instances = 0
    total_refs = 0

    for i, f in enumerate(files, start=1):
        try:
            stats = svc.ingest_file(f)
            ok += 1
            total_instances += int(stats.instances_upserted)
            total_refs += int(stats.refs_upserted)
            logger.info(
                f"[{i}/{len(files)}] OK {f.name} :: format={stats.format} instances={stats.instances_upserted} refs={stats.refs_upserted}"
            )
        except Exception as e:
            failed += 1
            logger.error(f"[{i}/{len(files)}] FAILED {f}: {e}")

    logger.success(
        "Bulk STEP ingestion complete: "
        f"files_ok={ok} files_failed={failed} total_instances={total_instances} total_refs={total_refs}"
    )

    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
