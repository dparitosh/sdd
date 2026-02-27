#!/usr/bin/env python3
"""Ingest OWL/RDF ontology reference data into Neo4j.

This script is the CLI companion to `src.web.services.ontology_ingest_service`.
It exists for repeatable, version-controlled ingestion runs (CI, ops, local dev).

Examples:
  - Ingest the MoSSEC AP243 ontology shipped in this repo:
      python backend/scripts/ingest_ontology_rdf.py --path smrlv12/data/domain_models/mossec/ap243_v1.owl

  - Ingest a Turtle file:
      python backend/scripts/ingest_ontology_rdf.py --path data/uploads/emmo.ttl --format turtle --name EMMO
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend root to path (backend/ contains the `src` package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file
load_dotenv(PROJECT_ROOT / ".env")

from src.web.services.ontology_ingest_service import OntologyIngestService, OntologyIngestConfig  # pyright: ignore[reportMissingImports, reportMissingModuleSource]


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest OWL/RDF ontology into Neo4j")
    parser.add_argument(
        "--path",
        required=True,
        help="Path to ontology file (.owl/.ttl/.rdf/.xml/.jsonld)",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Override ontology name (defaults to owl:Ontology title/label or file stem)",
    )
    parser.add_argument(
        "--format",
        default=None,
        help="Optional rdflib format hint (e.g., xml, turtle, json-ld)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Neo4j UNWIND batch size",
    )

    args = parser.parse_args()

    load_dotenv()

    cfg = OntologyIngestConfig(batch_size=args.batch_size)
    svc = OntologyIngestService(cfg)

    rdf_path = Path(args.path).resolve()
    stats = svc.ingest_file(rdf_path, ontology_name=args.name, rdf_format=args.format)

    logger.success(
        "Ontology ingestion complete: "
        f"name={stats.ontology_name} classes={stats.classes_upserted} "
        f"subclass_rels={stats.subclass_rels_upserted} units={stats.units_upserted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
