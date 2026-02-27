#!/usr/bin/env python3
"""Ingest STEP instance files into Neo4j.

Supports:
- .stp/.step (ISO 10303-21 Part 21 clear text)
- .stpx (ISO 10303-28 STEP-XML) best-effort

This is a lightweight ingestion: it stores raw instances and references so you
can query them in Neo4j and then build AP242 mappings on top.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from loguru import logger

from src.parsers.step_parser import detect_step_format, iter_part21_entities, iter_stepx_refs, parse_step_metadata  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
from src.web.services.step_ingest_service import StepIngestConfig, StepIngestService  # pyright: ignore[reportMissingImports, reportMissingModuleSource]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest STEP (.stp/.step/.stpx) into Neo4j")
    parser.add_argument("--path", required=True, help="Path to STEP file")
    parser.add_argument("--label", default=None, help="Optional display name/label")
    parser.add_argument(
        "--analyze-only",
        action="store_true",
        help="Parse and print basic stats without connecting to Neo4j",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Neo4j UNWIND batch size (default: 500)",
    )
    args = parser.parse_args()

    load_dotenv()

    step_path = Path(args.path).resolve()

    if args.analyze_only:
        meta = parse_step_metadata(step_path)
        fmt = detect_step_format(step_path)

        instances = 0
        refs = 0
        if fmt == "p21":
            for e in iter_part21_entities(step_path):
                instances += 1
                refs += len(e.ref_ids)
        elif fmt == "stpx":
            try:
                refs = sum(1 for _ in iter_stepx_refs(step_path))
            except (OSError, ET.ParseError) as e:
                logger.warning(f"Failed to parse STEP-XML refs: {e}")
                refs = 0

        logger.info(
            "STEP analysis: "
            f"format={fmt} schema={meta.file_schema} file_name={meta.file_name} "
            f"instances={instances} refs={refs}"
        )
        return 0

    svc = StepIngestService(StepIngestConfig(batch_size=args.batch_size))
    stats = svc.ingest_file(step_path, file_label=args.label)

    logger.success(
        "STEP ingestion complete: "
        f"format={stats.format} schema={stats.file_schema} "
        f"instances={stats.instances_upserted} refs={stats.refs_upserted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
