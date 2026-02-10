"""STEP (.stp/.step/.stpx) ingestion service.

Goal
----
Provide a modular ingestion layer that can be invoked:
- from scripts (offline ingestion)
- from FastAPI endpoints (agents can call it via OpenAPI)

This service ingests STEP *instance* data as a lightweight graph:
- :StepFile nodes represent a file
- :StepInstance nodes represent instance records within the file
- :STEP_REF relationships represent raw instance references (#id -> #id)

It does **not** attempt full AP242 semantic mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

from loguru import logger

from src.parsers.step_parser import (
    StepFileMeta,
    detect_step_format,
    iter_part21_entities,
    iter_stepx_refs,
    parse_step_metadata,
)
from src.web.services import get_neo4j_service


@dataclass(frozen=True)
class StepIngestConfig:
    batch_size: int = 500


@dataclass(frozen=True)
class StepIngestStats:
    file_uri: str
    format: str
    file_schema: Optional[str]
    instances_upserted: int
    refs_upserted: int


class StepIngestService:
    def __init__(self, config: StepIngestConfig | None = None):
        self.config = config or StepIngestConfig()
        self.neo4j = get_neo4j_service()

    def ingest_file(self, path: Path, *, file_label: Optional[str] = None) -> StepIngestStats:
        if not path.exists():
            raise FileNotFoundError(str(path))

        # Defensive logging: STEP files can be very large.
        try:
            size_mb = path.stat().st_size / (1024 * 1024)
            if size_mb > 200:
                logger.warning(
                    f"Large STEP file detected ({size_mb:.1f} MB). "
                    "Ingestion reads the file as text and may be slow/memory-heavy. "
                    "Consider ingesting a smaller sample first."
                )
        except OSError:
            # Non-fatal: continue.
            pass

        meta = parse_step_metadata(path)
        fmt = detect_step_format(path)

        file_uri = str(path.resolve())
        name = file_label or path.name

        logger.info(f"STEP ingest: path={path} format={fmt} schema={meta.file_schema}")

        self._ensure_step_file_node(file_uri=file_uri, name=name, meta=meta)

        instances_upserted = 0
        refs_upserted = 0

        if fmt == "p21":
            # Stream parse + ingest in batches. This avoids holding the full file's
            # instances/refs in memory and ensures ingestion progresses incrementally.
            instances_upserted, refs_upserted = self._ingest_part21_streaming(
                path=path,
                file_uri=file_uri,
                meta=meta,
            )
        elif fmt == "stpx":
            # Best-effort: only ingest refs (ids are not normalized here).
            try:
                refs = list(iter_stepx_refs(path))
            except (OSError, ET.ParseError) as e:
                logger.warning(f"Failed to parse STEP-XML refs for {path}: {e}")
                refs = []
            refs_upserted = self._upsert_stepx_refs(file_uri, refs)
        else:
            logger.warning("Unknown STEP format; only StepFile metadata node was created")

        return StepIngestStats(
            file_uri=file_uri,
            format=fmt,
            file_schema=meta.file_schema,
            instances_upserted=instances_upserted,
            refs_upserted=refs_upserted,
        )

    def _ingest_part21_streaming(self, *, path: Path, file_uri: str, meta: StepFileMeta) -> tuple[int, int]:
        """Ingest Part-21 instances and refs in a single streaming pass.

        We ingest instances and references in separate UNWIND batches, but we
        *do not* materialize the entire entity list first.

        Note: Reference ingestion uses MERGE for endpoint nodes to tolerate
        forward references (to_id not ingested yet).
        """

        batch_size = max(1, int(self.config.batch_size))

        inst_rows: list[dict] = []
        ref_rows: list[dict] = []
        instances = 0
        refs = 0

        for e in iter_part21_entities(path):
            instances += 1

            inst_rows.append(
                {
                    "file_uri": file_uri,
                    "id": e.step_id,
                    "entity_type": e.entity_type,
                    "raw": e.raw,
                    "raw_args": e.raw_args,
                    "file_schema": meta.file_schema,
                }
            )

            if e.ref_ids:
                for ref in e.ref_ids:
                    refs += 1
                    ref_rows.append(
                        {
                            "file_uri": file_uri,
                            "from_id": e.step_id,
                            "to_id": ref,
                        }
                    )

            if len(inst_rows) >= batch_size:
                self._upsert_part21_instances_rows(inst_rows)
                inst_rows.clear()

            if len(ref_rows) >= batch_size:
                self._upsert_part21_refs_rows(ref_rows)
                ref_rows.clear()

        if inst_rows:
            self._upsert_part21_instances_rows(inst_rows)
        if ref_rows:
            self._upsert_part21_refs_rows(ref_rows)

        return instances, refs

    def _ensure_step_file_node(self, *, file_uri: str, name: str, meta: StepFileMeta) -> None:
        # Map some known schemas to ap metadata when possible.
        ap_schema = None
        ap_level = None
        if meta.file_schema:
            upper = meta.file_schema.upper()
            if "AP242" in upper:
                ap_schema = "AP242"
                ap_level = 2
            elif "AP239" in upper:
                ap_schema = "AP239"
                ap_level = 1
            elif "AP243" in upper:
                ap_schema = "AP243"
                ap_level = 3

        cypher = """
        MERGE (f:StepFile {uri: $uri})
        SET f.name = $name,
            f.format = $format,
            f.file_schema = $file_schema,
            f.file_name = $file_name,
            f.ap_schema = $ap_schema,
            f.ap_level = $ap_level,
            f.updated_on = datetime()
        """
        self.neo4j.execute_query(
            cypher,
            {
                "uri": file_uri,
                "name": name,
                "format": meta.format,
                "file_schema": meta.file_schema,
                "file_name": meta.file_name,
                "ap_schema": ap_schema,
                "ap_level": ap_level,
            },
        )

    def _upsert_part21_instances_rows(self, rows) -> int:
        cypher = """
        UNWIND $rows AS row
        MERGE (i:StepInstance {file_uri: row.file_uri, step_id: row.id})
        SET i.entity_type = row.entity_type,
            i.raw = row.raw,
            i.raw_args = row.raw_args,
            i.file_schema = row.file_schema,
            i.updated_on = datetime()
        WITH i, row
        MERGE (t:StepEntityType {name: row.entity_type})
        SET t.updated_on = datetime()
        MERGE (i)-[:INSTANCE_OF]->(t)
        WITH i, row, t
        MATCH (f:StepFile {uri: row.file_uri})
        MERGE (f)-[:CONTAINS]->(i)
        WITH row, t
        CALL {
            WITH row
            OPTIONAL MATCH (c:Class) 
            WHERE toUpper(c.name) = toUpper(replace(row.entity_type, '_', '')) 
                  OR toUpper(c.name) = row.entity_type
            RETURN c AS mbse_class
            LIMIT 1
        }
        CALL {
            WITH row
            OPTIONAL MATCH (x:XSDElement) 
            WHERE toUpper(x.name) = row.entity_type
            RETURN x AS xsd_element
            LIMIT 1
        }
        FOREACH (_ IN CASE WHEN mbse_class IS NULL THEN [] ELSE [1] END | MERGE (t)-[:ALIGNS_TO]->(mbse_class))
        FOREACH (_ IN CASE WHEN xsd_element IS NULL THEN [] ELSE [1] END | MERGE (t)-[:ALIGNS_TO]->(xsd_element))
        """

        # Snapshot the rows before executing, because the Neo4j driver may
        # serialize parameters lazily. Callers commonly reuse/clear lists.
        batch = list(rows)
        self.neo4j.execute_query(cypher, {"rows": batch})
        return len(batch)

    def _upsert_part21_refs_rows(self, rows) -> int:
        if not rows:
            return 0

        cypher = """
        UNWIND $rows AS row
        MATCH (f:StepFile {uri: row.file_uri})
        MERGE (a:StepInstance {file_uri: row.file_uri, step_id: row.from_id})
        MERGE (b:StepInstance {file_uri: row.file_uri, step_id: row.to_id})
        MERGE (f)-[:CONTAINS]->(a)
        MERGE (f)-[:CONTAINS]->(b)
        MERGE (a)-[:STEP_REF]->(b)
        """

        # Snapshot for safety; callers typically clear the list after flushing.
        batch = list(rows)
        self.neo4j.execute_query(cypher, {"rows": batch})
        return len(batch)

    def _upsert_stepx_refs(self, file_uri: str, refs) -> int:
        # STEP-XML ids are strings; we store them as step_id_str.
        batch_size = max(1, int(self.config.batch_size))

        rows = []
        for from_id, attr, to_id in refs:
            rows.append(
                {
                    "file_uri": file_uri,
                    "from_id": from_id,
                    "to_id": to_id,
                    "attr": attr,
                }
            )

        if not rows:
            return 0

        cypher = """
        UNWIND $rows AS row
        MERGE (a:StepXmlInstance {file_uri: row.file_uri, step_id_str: row.from_id})
        MERGE (b:StepXmlInstance {file_uri: row.file_uri, step_id_str: row.to_id})
        MERGE (a)-[r:STEPX_REF {attr: row.attr}]->(b)
        WITH row
        MATCH (f:StepFile {uri: row.file_uri})
        MERGE (f)-[:CONTAINS]->(:StepXmlInstance {file_uri: row.file_uri, step_id_str: row.from_id})
        """

        total = 0
        for i in range(0, len(rows), batch_size):
            chunk = rows[i : i + batch_size]
            self.neo4j.execute_query(cypher, {"rows": chunk})
            total += len(chunk)
        return total
