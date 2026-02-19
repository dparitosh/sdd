"""
OslcIngester – BaseIngester wrapper for OWL/RDF ontology and OSLC seed data.

Handles two ingestion flavours:

1. **OSLC seed TTLs** (``backend/data/seed/oslc/*.ttl``) – lightweight RDF
   with ``OntologyClass``, ``OntologyProperty``, ``Ontology`` nodes.
2. **External OWL ontologies** (any RDF file) – ingested via the existing
   :class:`OntologyIngestService` logic producing ``ExternalOwlClass``,
   ``ExternalUnit``, ``ValueType``, ``Classification`` nodes.

Both paths funnel through the :class:`GraphStore` protocol instead of
reaching for the ``get_neo4j_service()`` singleton, which means the same
code works against Neo4j, Apache Spark (Neo4j Spark Connector), etc.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    from rdflib import Graph as RDFGraph, Literal, RDF, RDFS, OWL, URIRef  # type: ignore[import-not-found]
    from rdflib.namespace import DCTERMS, SKOS  # type: ignore[import-not-found]
except ImportError:
    RDFGraph = None  # type: ignore[assignment,misc]

from src.engine.protocol import BaseIngester, GraphStore, IngestionResult
from src.engine.registry import registry


# ── helpers ──────────────────────────────────────────────────────────────

_AP_PATTERN = re.compile(r"ap[_-]?(239|242|243)", re.IGNORECASE)


def _detect_ap_level(uri: str) -> str:
    """Heuristic: try to extract AP level from a URI or filename."""
    m = _AP_PATTERN.search(uri)
    if m:
        return f"AP{m.group(1)}"
    return "Core"


def _local_name(uri: str) -> str:
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    return uri.rstrip("/").rsplit("/", 1)[-1]


def _first_literal(g, s, p) -> Optional[str]:
    for o in g.objects(s, p):
        if isinstance(o, Literal):
            text = str(o).strip()
            if text:
                return text
    return None


# ── OSLC seed loader (lightweight TTL → Ontology/OntologyClass/Property) ─


def _ingest_oslc_seed(
    store: GraphStore,
    ttl_path: Path,
) -> Dict[str, int]:
    """
    Parse a single OSLC seed TTL and MERGE its classes / properties.

    Returns a dict with simple counts.
    """
    if RDFGraph is None:
        raise ImportError("rdflib is required for OSLC ingestion")

    g = RDFGraph()
    g.parse(str(ttl_path), format="turtle")
    source_label = ttl_path.stem
    counts: Dict[str, int] = {"classes": 0, "properties": 0, "ontologies": 0}

    # ── Ontology node ────────────────────────────────────────────────
    for s in g.subjects(RDF.type, OWL.Ontology):
        if not isinstance(s, URIRef):
            continue
        uri = str(s)
        label = _first_literal(g, s, RDFS.label) or _first_literal(g, s, DCTERMS.title) or source_label
        ap_level = _detect_ap_level(uri) or _detect_ap_level(str(ttl_path))
        store.execute_write(
            """
            MERGE (o:Ontology {uri: $uri})
            SET o.label = $label, o.source = $source, o.ap_level = $ap_level
            """,
            {"uri": uri, "label": label, "source": source_label, "ap_level": ap_level},
        )
        counts["ontologies"] += 1

    # ── OntologyClass nodes ──────────────────────────────────────────
    seen_classes: set = set()
    for class_type in (OWL.Class, RDFS.Class):
        for s in g.subjects(RDF.type, class_type):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            if uri in seen_classes:
                continue
            seen_classes.add(uri)
            label = _first_literal(g, s, RDFS.label) or _local_name(uri)
            comment = _first_literal(g, s, RDFS.comment) or ""
            ap_level = _detect_ap_level(uri) or _detect_ap_level(str(ttl_path))

            # Superclass extraction
            superclasses: List[str] = []
            for o in g.objects(s, RDFS.subClassOf):
                if isinstance(o, URIRef):
                    superclasses.append(str(o))

            store.execute_write(
                """
                MERGE (c:OntologyClass {uri: $uri})
                SET c.label = $label,
                    c.comment = $comment,
                    c.source = $source,
                    c.ap_level = $ap_level,
                    c.superclasses = $superclasses
                """,
                {
                    "uri": uri,
                    "label": label,
                    "comment": comment,
                    "source": source_label,
                    "ap_level": ap_level,
                    "superclasses": superclasses,
                },
            )
            counts["classes"] += 1

            # Link to ontology
            store.execute_write(
                """
                MATCH (c:OntologyClass {uri: $class_uri})
                MATCH (o:Ontology)
                WHERE c.source = o.source
                MERGE (o)-[:DEFINES]->(c)
                """,
                {"class_uri": uri},
            )

    # ── OntologyProperty nodes ───────────────────────────────────────
    for prop_type in (OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property):
        for s in g.subjects(RDF.type, prop_type):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            label = _first_literal(g, s, RDFS.label) or _local_name(uri)
            comment = _first_literal(g, s, RDFS.comment) or ""
            ap_level = _detect_ap_level(uri) or _detect_ap_level(str(ttl_path))

            domain_uri = None
            for o in g.objects(s, RDFS.domain):
                if isinstance(o, URIRef):
                    domain_uri = str(o)
                    break
            range_uri = None
            for o in g.objects(s, RDFS.range):
                if isinstance(o, URIRef):
                    range_uri = str(o)
                    break

            store.execute_write(
                """
                MERGE (p:OntologyProperty {uri: $uri})
                SET p.label = $label,
                    p.comment = $comment,
                    p.source = $source,
                    p.ap_level = $ap_level,
                    p.domain = $domain,
                    p.range = $range
                """,
                {
                    "uri": uri,
                    "label": label,
                    "comment": comment,
                    "source": source_label,
                    "ap_level": ap_level,
                    "domain": domain_uri,
                    "range": range_uri,
                },
            )
            counts["properties"] += 1

            # Link property → domain class
            if domain_uri:
                store.execute_write(
                    """
                    MATCH (p:OntologyProperty {uri: $prop_uri})
                    MATCH (c:OntologyClass {uri: $class_uri})
                    MERGE (c)-[:HAS_PROPERTY]->(p)
                    """,
                    {"prop_uri": uri, "class_uri": domain_uri},
                )

    return counts


# ── External OWL ontology loader (heavier: ExternalOwlClass, etc.) ───────


def _ingest_external_owl(
    store: GraphStore,
    rdf_path: Path,
    *,
    rdf_format: Optional[str] = None,
    ontology_name: Optional[str] = None,
    ap_level: int = 3,
    ap_schema: str = "AP243",
    ap_standard: str = "AP243",
    batch_size: int = 500,
) -> Dict[str, int]:
    """
    Parse an OWL/RDF file and MERGE into Neo4j via *store*.

    This replicates the core logic of
    :class:`OntologyIngestService.ingest_file` but routed through
    ``GraphStore`` instead of the ``neo4j_service`` singleton.
    """
    if RDFGraph is None:
        raise ImportError("rdflib is required for ontology ingestion")

    g = RDFGraph()
    g.parse(str(rdf_path), format=rdf_format)

    # Detect ontology identity
    ontology_iri: Optional[str] = None
    resolved_name = ontology_name or rdf_path.stem
    for s in g.subjects(RDF.type, OWL.Ontology):
        if isinstance(s, URIRef):
            ontology_iri = str(s)
            title = _first_literal(g, s, DCTERMS.title) or _first_literal(g, s, RDFS.label)
            if title and not ontology_name:
                resolved_name = title
            break

    logger.info(
        f"[oslc] Ontology: name={resolved_name} iri={ontology_iri} "
        f"triples={len(g)}"
    )

    # Ensure ontology node
    merge_key = "uri" if ontology_iri else "name"
    store.execute_write(
        f"""
        MERGE (o:ExternalOntology {{{merge_key}: ${merge_key}}})
        SET o.name = $name, o.uri = $uri, o.source_file = $source_file,
            o.loaded_on = datetime(), o.ap_level = $ap_level,
            o.ap_schema = $ap_schema, o.ap_standard = $ap_standard
        """,
        {
            "name": resolved_name,
            "uri": ontology_iri,
            "source_file": str(rdf_path),
            "ap_level": ap_level,
            "ap_schema": ap_schema,
            "ap_standard": ap_standard,
        },
    )

    # Extract + upsert classes
    classes = _extract_owl_classes(g, resolved_name, ap_level, ap_schema, ap_standard)
    classes_upserted = _batch_upsert(store, _UPSERT_CLASSES_CQL, classes, batch_size,
                                      ap_level=ap_level, ap_schema=ap_schema, ap_standard=ap_standard)

    # Subclass / equivalent edges
    subclass_edges, equiv_edges = _extract_class_edges(g)
    sub_upserted = _batch_upsert_edges(store, "SUBCLASS_OF", subclass_edges, batch_size,
                                         resolved_name, ap_level, ap_schema, ap_standard)
    eq_upserted = _batch_upsert_edges(store, "EQUIVALENT_CLASS", equiv_edges, batch_size,
                                        resolved_name, ap_level, ap_schema, ap_standard)

    # Link resources to ontology
    store.execute_write(
        """
        MATCH (o:ExternalOntology {name: $name})
        WITH o
        MATCH (n)
        WHERE n.ontology = $name AND n.ap_level = $ap_level
        MERGE (o)-[:DEFINES_REFERENCE_DATA]->(n)
        """,
        {"name": resolved_name, "ap_level": ap_level},
    )

    return {
        "ontology_iri": ontology_iri or "",
        "ontology_name": resolved_name,
        "triples": len(g),
        "classes_upserted": classes_upserted,
        "subclass_rels": sub_upserted,
        "equivalent_rels": eq_upserted,
    }


# ── private extraction helpers ───────────────────────────────────────────

def _extract_owl_classes(g, ont_name, ap_level, ap_schema, ap_standard):
    out = []
    seen = set()
    for ct in (OWL.Class, RDFS.Class):
        for s in g.subjects(RDF.type, ct):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            if uri in seen:
                continue
            seen.add(uri)
            name = _first_literal(g, s, RDFS.label) or _first_literal(g, s, SKOS.prefLabel) or _local_name(uri)
            desc = _first_literal(g, s, RDFS.comment) or _first_literal(g, s, DCTERMS.description)
            out.append({
                "uri": uri,
                "name": name,
                "description": desc,
                "ontology": ont_name,
                "ap_level": ap_level,
                "ap_schema": ap_schema,
                "ap_standard": ap_standard,
            })
    return out


def _extract_class_edges(g) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    sub, eq = [], []
    for s, o in g.subject_objects(RDFS.subClassOf):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            sub.append((str(s), str(o)))
    for s, o in g.subject_objects(OWL.equivalentClass):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            eq.append((str(s), str(o)))
    return sub, eq


_UPSERT_CLASSES_CQL = """
UNWIND $rows AS row
MERGE (c:ExternalOwlClass {uri: row.uri})
SET c.name = row.name,
    c.description = row.description,
    c.ontology = row.ontology,
    c.ap_level = row.ap_level,
    c.ap_schema = row.ap_schema,
    c.ap_standard = row.ap_standard
RETURN count(c) AS count
"""


def _batch_upsert(store, cypher, rows, batch_size, **extra_params):
    total = 0
    for i in range(0, max(len(rows), 1), batch_size):
        batch = rows[i : i + batch_size]
        if not batch:
            break
        res = store.execute_query(cypher, {"rows": batch, **extra_params})
        total += int(res[0]["count"]) if res else 0
    return total


def _batch_upsert_edges(store, rel_type, edges, batch_size, ontology, ap_level, ap_schema, ap_standard):
    if not edges:
        return 0
    cypher = f"""
    UNWIND $rows AS row
    MERGE (a:ExternalOwlClass {{uri: row.from_uri}})
    MERGE (b:ExternalOwlClass {{uri: row.to_uri}})
    SET a.ap_level = $ap_level, a.ap_schema = $ap_schema, a.ap_standard = $ap_standard, a.ontology = $ontology,
        b.ap_level = $ap_level, b.ap_schema = $ap_schema, b.ap_standard = $ap_standard, b.ontology = $ontology
    MERGE (a)-[r:{rel_type}]->(b)
    SET r.ap_level = $ap_level, r.ap_schema = $ap_schema, r.ap_standard = $ap_standard
    RETURN count(r) AS count
    """
    rows = [{"from_uri": a, "to_uri": b} for a, b in edges]
    total = 0
    for i in range(0, max(len(rows), 1), batch_size):
        batch = rows[i : i + batch_size]
        if not batch:
            break
        res = store.execute_query(cypher, {
            "rows": batch,
            "ap_level": ap_level,
            "ap_schema": ap_schema,
            "ap_standard": ap_standard,
            "ontology": ontology,
        })
        total += int(res[0]["count"]) if res else 0
    return total


# ── Registered ingester ─────────────────────────────────────────────────


@registry.register
class OslcIngester(BaseIngester):
    """Ingest OSLC seed TTLs and/or external OWL ontologies into the KG."""

    @property
    def name(self) -> str:
        return "oslc"

    # -- constraints (shared with XMI – but idempotent) --------------------

    def create_constraints(self, store: GraphStore) -> IngestionResult:
        stmts = [
            "CREATE CONSTRAINT ontology_uri IF NOT EXISTS FOR (n:Ontology) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ontology_class_uri IF NOT EXISTS FOR (n:OntologyClass) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ontology_property_uri IF NOT EXISTS FOR (n:OntologyProperty) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ext_ontology_uri IF NOT EXISTS FOR (n:ExternalOntology) REQUIRE n.uri IS UNIQUE",
            "CREATE CONSTRAINT ext_owl_class_uri IF NOT EXISTS FOR (n:ExternalOwlClass) REQUIRE n.uri IS UNIQUE",
        ]
        created = 0
        for s in stmts:
            try:
                store.execute_write(s)
                created += 1
            except Exception:  # noqa: BLE001
                pass  # already exists – fine
        return IngestionResult(ingester_name=self.name, constraints_created=created)

    # -- ingest ------------------------------------------------------------

    def ingest(
        self,
        store: GraphStore,
        source: Path | str,
        *,
        options: Optional[Dict[str, Any]] = None,
    ) -> IngestionResult:
        """
        Ingest OSLC data from *source*.

        *source* may be:
          - A directory → all ``*.ttl`` files are treated as OSLC seed TTLs.
          - A single ``.ttl`` / ``.rdf`` / ``.owl`` file → ingested as
            either OSLC seed (lightweight) or external OWL (full extraction)
            depending on the ``mode`` option.

        Options
        -------
        mode : str
            ``"seed"`` (default) – lightweight OSLC TTL ingestion.
            ``"owl"``           – full ExternalOwlClass extraction.
        ontology_name : str, optional
            Override the detected ontology name.
        """
        opts = options or {}
        mode = opts.get("mode", "seed")
        source = Path(source)

        total_nodes = 0
        total_rels = 0
        errors: List[str] = []
        extra: Dict[str, Any] = {}

        files: List[Path] = []
        if source.is_dir():
            files = sorted(source.glob("*.ttl"))
        elif source.is_file():
            files = [source]
        else:
            errors.append(f"Source not found: {source}")

        for f in files:
            logger.info(f"[oslc] ingesting {f} (mode={mode})")
            try:
                if mode == "owl":
                    counts = _ingest_external_owl(
                        store, f,
                        ontology_name=opts.get("ontology_name"),
                    )
                    total_nodes += counts.get("classes_upserted", 0)
                    total_rels += counts.get("subclass_rels", 0) + counts.get("equivalent_rels", 0)
                else:
                    counts = _ingest_oslc_seed(store, f)
                    total_nodes += counts.get("classes", 0) + counts.get("properties", 0) + counts.get("ontologies", 0)

                extra[f.name] = counts
            except Exception as exc:
                msg = f"Error ingesting {f.name}: {exc}"
                logger.error(msg)
                errors.append(msg)

        return IngestionResult(
            ingester_name=self.name,
            source_file=str(source),
            nodes_created=total_nodes,
            relationships_created=total_rels,
            errors=errors,
            extra=extra,
        )
