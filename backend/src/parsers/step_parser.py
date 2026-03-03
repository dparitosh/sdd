"""STEP file parsing helpers.

Scope
-----
This module provides *lightweight* parsing for:
- ISO 10303-21 (Part 21) clear text encoding: .stp/.step
- ISO 10303-28 (Part 28) STEP-XML: .stpx (best-effort)

It is intentionally not a full STEP/AP242 semantic mapper.
Instead it extracts:
- FILE_SCHEMA / FILE_NAME metadata (when available)
- instance records (#id = ENTITY_NAME(...);) for Part 21
- basic XML instance ids/refs for Part 28 (best-effort)

The goal is to enable ingesting STEP instance graphs into Neo4j as
queryable raw reference data that can later be mapped into AP242 domain
labels.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Optional
import re
import xml.etree.ElementTree as ET


_PART21_SCHEMA_RE = re.compile(r"FILE_SCHEMA\s*\(\s*\(\s*'([^']+)'\s*\)\s*\)\s*;", re.IGNORECASE)
_PART21_FILENAME_RE = re.compile(r"FILE_NAME\s*\(\s*'([^']*)'\s*,", re.IGNORECASE)


@dataclass(frozen=True)
class StepFileMeta:
    format: str  # 'p21' | 'stpx' | 'unknown'
    file_schema: Optional[str]
    file_name: Optional[str]


@dataclass(frozen=True)
class StepP21Entity:
    step_id: int
    entity_type: str
    raw_args: str
    raw: str
    ref_ids: tuple[int, ...]


def detect_step_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".stp", ".step"}:
        return "p21"
    if suffix == ".stpx":
        return "stpx"
    # Fallback: sniff header
    try:
        head = path.read_text(encoding="utf-8", errors="ignore")[:2048]
    except OSError:
        return "unknown"

    if "ISO-10303-21" in head:
        return "p21"
    if "iso_10303_28" in head or "ISO_10303_28" in head:
        return "stpx"
    return "unknown"


def parse_step_metadata(path: Path) -> StepFileMeta:
    fmt = detect_step_format(path)

    if fmt == "p21":
        text = path.read_text(encoding="utf-8", errors="ignore")
        schema = _match_first(_PART21_SCHEMA_RE, text)
        fname = _match_first(_PART21_FILENAME_RE, text)
        return StepFileMeta(format=fmt, file_schema=schema, file_name=fname)

    if fmt == "stpx":
        # Best-effort: attempt to parse root and find schema-ish attributes.
        try:
            tree = ET.parse(str(path))
            root = tree.getroot()
            # Common attribute: schemaName / schema_name / schema
            schema = (
                root.attrib.get("schemaName")
                or root.attrib.get("schema_name")
                or root.attrib.get("schema")
            )
            return StepFileMeta(format=fmt, file_schema=schema, file_name=path.name)
        except (OSError, ET.ParseError):
            return StepFileMeta(format=fmt, file_schema=None, file_name=path.name)

    return StepFileMeta(format=fmt, file_schema=None, file_name=path.name)


def iter_part21_entities(path: Path) -> Iterator[StepP21Entity]:
    """Iterate over Part-21 instance statements.

    We split on ';' outside of single-quoted strings to handle multi-line entities.
    This is a pragmatic parser meant for ingestion and exploration.
    """

    text = path.read_text(encoding="utf-8", errors="ignore")

    # Reduce /* ... */ comments (best-effort, non-nested)
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)

    in_str = False
    buf: list[str] = []

    def flush(stmt: str) -> Optional[str]:
        s = stmt.strip()
        if not s:
            return None
        return s

    for ch in text:
        if ch == "'":
            # STEP uses '' to escape quotes inside strings. We handle minimally by toggling
            # state and letting doubled quotes be processed as two toggles; this is good
            # enough for statement splitting.
            in_str = not in_str
            buf.append(ch)
            continue

        if ch == ";" and not in_str:
            stmt = flush("".join(buf))
            buf = []
            if stmt is None:
                continue
            ent = _parse_part21_entity_statement(stmt)
            if ent:
                yield ent
            continue

        buf.append(ch)


_PART21_ENTITY_RE = re.compile(r"^#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*)\)\s*$", re.IGNORECASE | re.DOTALL)


def _parse_part21_entity_statement(stmt: str) -> Optional[StepP21Entity]:
    # We only ingest instance statements.
    if not stmt.startswith("#"):
        return None

    m = _PART21_ENTITY_RE.match(stmt)
    if not m:
        return None

    step_id = int(m.group(1))
    entity_type = m.group(2).upper()
    args = m.group(3).strip()

    ref_ids = tuple(sorted(set(_extract_ref_ids(args))))
    return StepP21Entity(
        step_id=step_id,
        entity_type=entity_type,
        raw_args=args,
        raw=stmt + ";",
        ref_ids=ref_ids,
    )


_REF_RE = re.compile(r"#(\d+)")


def _extract_ref_ids(args: str) -> Iterable[int]:
    # Remove string literals so we don't pick up '#123' inside a quoted value.
    scrubbed = re.sub(r"'(?:[^']|'')*'", "''", args)
    for m in _REF_RE.finditer(scrubbed):
        try:
            yield int(m.group(1))
        except ValueError:
            continue


def iter_stepx_refs(path: Path) -> Iterator[tuple[str, str, str]]:
    """Best-effort iterator for STEP-XML references.

    Yields tuples: (from_id, attr, to_id)

    This is intentionally conservative. We only treat attributes named 'ref' or
    ending with 'ref' as references.
    """

    tree = ET.parse(str(path))
    root = tree.getroot()

    # STEP-XML uses a wide variety of patterns; we scan for attributes that look
    # like ids and refs.
    for elem in root.iter():
        from_id = elem.attrib.get("id") or elem.attrib.get("ID")
        if not from_id:
            continue

        for k, v in elem.attrib.items():
            kl = k.lower()
            if kl == "ref" or kl.endswith("ref"):
                if v:
                    yield (from_id, k, v)


def _match_first(rx: re.Pattern[str], text: str) -> Optional[str]:
    m = rx.search(text)
    if not m:
        return None
    return m.group(1)
