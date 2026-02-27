"""Ontology ingestion service (OWL/RDF -> Neo4j).

Goal
----
Provide a modular, reusable ingestion layer that can be invoked:
- from scripts (offline batch ingestion)
- from FastAPI endpoints (so agents can use it as a tool via OpenAPI)

This service intentionally focuses on *reference data* for AP243-like workflows:
- External ontology classes -> :ExternalOwlClass
- Units -> :ExternalUnit (best-effort detection for common vocabularies)
- Value types -> :ValueType (best-effort derived from datatype properties)
- Classifications -> :Classification (best-effort derived from SKOS concepts)

The ingestion is designed to be incremental and idempotent via MERGE on `uri`.

Notes
-----
- We set `ap_level='AP243'` and `ap_schema='AP243'` to match the current REST API filters.
- We also store `ap_standard='AP243'` for humans and compatibility with older scripts.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from loguru import logger

try:
    from rdflib import Graph, Literal, RDF, RDFS, OWL, URIRef  # type: ignore[import-not-found]
    from rdflib.namespace import DCTERMS, SKOS  # type: ignore[import-not-found]
except Exception as e:  # pragma: no cover
    raise ImportError(
        "rdflib is required for ontology ingestion. Install backend requirements (rdflib>=7.0.0)."
    ) from e

from src.web.services import get_neo4j_service


@dataclass(frozen=True)
class OntologyIngestConfig:
    ap_level: str = "AP243"       # override per-request (e.g. "AP239", "AP242")
    ap_schema: str = "AP243"
    ap_standard: str = "AP243"
    batch_size: int = 500


@dataclass(frozen=True)
class OntologyIngestStats:
    ontology_iri: Optional[str]
    ontology_name: str
    triples: int
    classes_upserted: int
    subclass_rels_upserted: int
    equivalent_rels_upserted: int
    units_upserted: int
    value_types_upserted: int
    classifications_upserted: int


class OntologyIngestService:
    """Parse an OWL/RDF file and upsert key nodes/relationships into Neo4j."""

    def __init__(self, config: OntologyIngestConfig | None = None):
        self.config = config or OntologyIngestConfig()
        self.neo4j = get_neo4j_service()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------

    def ingest_file(
        self,
        rdf_path: Path,
        *,
        ontology_name: Optional[str] = None,
        rdf_format: Optional[str] = None,
    ) -> OntologyIngestStats:
        if not rdf_path.exists():
            raise FileNotFoundError(str(rdf_path))

        g = Graph()
        logger.info(f"Parsing ontology RDF: {rdf_path}")
        g.parse(str(rdf_path), format=rdf_format)

        ontology_iri, resolved_name = self._detect_ontology_identity(g, rdf_path)
        if ontology_name:
            resolved_name = ontology_name

        triples = len(g)
        logger.info(
            f"Ontology parsed: name={resolved_name} iri={ontology_iri} triples={triples}"
        )

        self._ensure_ontology_node(
            ontology_iri=ontology_iri,
            ontology_name=resolved_name,
            source_file=str(rdf_path),
        )

        classes = self._extract_classes(g, resolved_name)
        subclass_edges, equiv_edges = self._extract_class_edges(g)
        object_props = self._extract_object_properties(g, resolved_name)
        datatype_props = self._extract_datatype_properties(g, resolved_name)

        units = self._extract_units(g, resolved_name)
        value_types = self._extract_value_types(g, resolved_name)
        classifications = self._extract_classifications(g, resolved_name)

        classes_upserted = self._upsert_external_owl_classes(classes)
        subclass_rels_upserted = self._upsert_class_edges(
            rel_type="SUBCLASS_OF", edges=subclass_edges, ontology_name=resolved_name
        )
        equivalent_rels_upserted = self._upsert_class_edges(
            rel_type="EQUIVALENT_CLASS", edges=equiv_edges, ontology_name=resolved_name
        )
        self._upsert_owl_object_properties(object_props)
        self._upsert_owl_datatype_properties(datatype_props)

        units_upserted = self._upsert_external_units(units)
        value_types_upserted = self._upsert_value_types(value_types)
        classifications_upserted = self._upsert_classifications(classifications)

        # Link all ingested resources to ontology node (best-effort)
        self._link_resources_to_ontology(resolved_name)

        return OntologyIngestStats(
            ontology_iri=ontology_iri,
            ontology_name=resolved_name,
            triples=triples,
            classes_upserted=classes_upserted,
            subclass_rels_upserted=subclass_rels_upserted,
            equivalent_rels_upserted=equivalent_rels_upserted,
            units_upserted=units_upserted,
            value_types_upserted=value_types_upserted,
            classifications_upserted=classifications_upserted,
        )

    # ---------------------------------------------------------------------
    # Detection + extraction
    # ---------------------------------------------------------------------

    def _detect_ontology_identity(self, g: Graph, rdf_path: Path) -> Tuple[Optional[str], str]:
        # Prefer explicit owl:Ontology declaration
        for s in g.subjects(RDF.type, OWL.Ontology):
            if not isinstance(s, URIRef):
                continue
            iri = str(s)
            title = self._first_literal(g, s, DCTERMS.title) or self._first_literal(
                g, s, RDFS.label
            )
            if title:
                return iri, title
            return iri, rdf_path.stem

        # Fallback: try to infer from base namespace or file stem
        return None, rdf_path.stem

    def _extract_classes(self, g: Graph, ontology_name: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []

        class_types = (OWL.Class, RDFS.Class)
        seen: set[str] = set()

        for ct in class_types:
            for s in g.subjects(RDF.type, ct):
                if not isinstance(s, URIRef):
                    continue
                uri = str(s)
                if uri in seen:
                    continue
                seen.add(uri)

                name = (
                    self._first_literal(g, s, RDFS.label)
                    or self._first_literal(g, s, SKOS.prefLabel)
                    or self._local_name(uri)
                )
                description = (
                    self._first_literal(g, s, RDFS.comment)
                    or self._first_literal(g, s, DCTERMS.description)
                    or None
                )

                out.append(
                    {
                        "uri": uri,
                        "name": name,
                        "description": description,
                        "ontology": ontology_name,
                        "ap_level": self.config.ap_level,
                        "ap_schema": self.config.ap_schema,
                        "ap_standard": self.config.ap_standard,
                    }
                )

        return out

    def _extract_class_edges(self, g: Graph) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        subclass_edges: List[Tuple[str, str]] = []
        equiv_edges: List[Tuple[str, str]] = []

        for s, o in g.subject_objects(RDFS.subClassOf):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                subclass_edges.append((str(s), str(o)))

        for s, o in g.subject_objects(OWL.equivalentClass):
            if isinstance(s, URIRef) and isinstance(o, URIRef):
                equiv_edges.append((str(s), str(o)))

        return subclass_edges, equiv_edges

    def _extract_units(self, g: Graph, ontology_name: str) -> List[Dict[str, Any]]:
        """Best-effort extraction for units.

        Many vocabularies exist (QUDT, OM, EMMO patterns). We detect common cases:
        - rdf:type qudt:Unit
        - rdf:type om:Unit
        """

        out: List[Dict[str, Any]] = []

        # Common unit classes (by URI string to avoid hard dependency on namespaces)
        unit_type_uris = {
            "http://qudt.org/schema/qudt/Unit",
            "http://www.ontology-of-units-of-measure.org/resource/om-2/Unit",
        }

        seen: set[str] = set()
        for unit_type in unit_type_uris:
            for s in g.subjects(RDF.type, URIRef(unit_type)):
                if not isinstance(s, URIRef):
                    continue
                uri = str(s)
                if uri in seen:
                    continue
                seen.add(uri)

                name = (
                    self._first_literal(g, s, RDFS.label)
                    or self._first_literal(g, s, SKOS.prefLabel)
                    or self._local_name(uri)
                )

                # Common symbol predicates in QUDT/OM vary widely; store best-effort
                symbol = (
                    self._first_literal(g, s, URIRef("http://qudt.org/schema/qudt/symbol"))
                    or self._first_literal(g, s, URIRef("http://www.ontology-of-units-of-measure.org/resource/om-2/symbol"))
                    or None
                )

                out.append(
                    {
                        "uri": uri,
                        "name": name,
                        "symbol": symbol,
                        "unit_type": None,
                        "si_conversion": None,
                        "ontology": ontology_name,
                        "ap_level": self.config.ap_level,
                        "ap_schema": self.config.ap_schema,
                        "ap_standard": self.config.ap_standard,
                    }
                )

        return out

    def _extract_value_types(self, g: Graph, ontology_name: str) -> List[Dict[str, Any]]:
        """Best-effort extraction for value types.

        We treat owl:DatatypeProperty as a value-type candidate because it's a common
        bridge between reference data and typed properties.
        """

        out: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for s in g.subjects(RDF.type, OWL.DatatypeProperty):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            if uri in seen:
                continue
            seen.add(uri)

            name = (
                self._first_literal(g, s, RDFS.label)
                or self._first_literal(g, s, SKOS.prefLabel)
                or self._local_name(uri)
            )

            # Range (datatype)
            dt = None
            for o in g.objects(s, RDFS.range):
                if isinstance(o, URIRef):
                    dt = self._local_name(str(o))
                    break

            out.append(
                {
                    "uri": uri,
                    "name": name,
                    "data_type": dt,
                    "unit_reference": None,
                    "ontology": ontology_name,
                    "ap_level": self.config.ap_level,
                    "ap_schema": self.config.ap_schema,
                    "ap_standard": self.config.ap_standard,
                }
            )

        return out

    def _extract_classifications(self, g: Graph, ontology_name: str) -> List[Dict[str, Any]]:
        """Best-effort extraction for classifications based on SKOS concepts."""

        out: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for s in g.subjects(RDF.type, SKOS.Concept):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            if uri in seen:
                continue
            seen.add(uri)

            name = (
                self._first_literal(g, s, SKOS.prefLabel)
                or self._first_literal(g, s, RDFS.label)
                or self._local_name(uri)
            )
            code = self._first_literal(g, s, SKOS.notation)

            # Try to infer the scheme name
            system = None
            for scheme in g.objects(s, SKOS.inScheme):
                if isinstance(scheme, URIRef):
                    system = (
                        self._first_literal(g, scheme, DCTERMS.title)
                        or self._first_literal(g, scheme, RDFS.label)
                        or self._local_name(str(scheme))
                    )
                    break

            out.append(
                {
                    "uri": uri,
                    "name": name,
                    "classification_system": system or ontology_name,
                    "code": code,
                    "ontology": ontology_name,
                    "ap_level": self.config.ap_level,
                    "ap_schema": self.config.ap_schema,
                    "ap_standard": self.config.ap_standard,
                }
            )

        return out

    # ---------------------------------------------------------------------
    # Neo4j upserts
    # ---------------------------------------------------------------------

    def _ensure_ontology_node(
        self, *, ontology_iri: Optional[str], ontology_name: str, source_file: str
    ) -> None:
        # Prefer IRI as stable key (prevents duplicate ontology nodes across runs).
        # Use both :Ontology and :ExternalOntology so the STEP Ontology graph
        # view (which filters on fixedNodeTypes=['Ontology']) can find these nodes.
        if ontology_iri:
            cypher = """
            MERGE (o:ExternalOntology {uri: $uri})
            SET o:Ontology,
                o.name = $name,
                o.source_file = $source_file,
                o.loaded_on = datetime(),
                o.ap_level = $ap_level,
                o.ap_schema = $ap_schema,
                o.ap_standard = $ap_standard
            """
        else:
            cypher = """
            MERGE (o:ExternalOntology {name: $name})
            SET o:Ontology,
                o.uri = $uri,
                o.source_file = $source_file,
                o.loaded_on = datetime(),
                o.ap_level = $ap_level,
                o.ap_schema = $ap_schema,
                o.ap_standard = $ap_standard
            """

        params = {
            "name": ontology_name,
            "uri": ontology_iri,
            "source_file": source_file,
            "ap_level": self.config.ap_level,
            "ap_schema": self.config.ap_schema,
            "ap_standard": self.config.ap_standard,
        }
        self.neo4j.execute_query(cypher, params)

        # Best-effort de-duplication without APOC.
        # If prior runs created multiple ontology nodes with the same IRI (e.g., due to using name as key),
        # we consolidate them by:
        #   1) keeping one node
        #   2) reattaching :DEFINES_REFERENCE_DATA relationships
        #   3) deleting the duplicates
        if ontology_iri:
            dedupe = """
            MATCH (o:ExternalOntology {uri: $uri})
            WITH collect(o) AS os
            WHERE size(os) > 1
            WITH os[0] AS keep, os[1..] AS dups
            UNWIND dups AS d
            OPTIONAL MATCH (d)-[:DEFINES_REFERENCE_DATA]->(n)
            WITH keep, d, collect(DISTINCT n) AS ns
            FOREACH (n IN ns | MERGE (keep)-[:DEFINES_REFERENCE_DATA]->(n))
            DETACH DELETE d
            RETURN count(*) AS deduped
            """
            try:
                self.neo4j.execute_query(dedupe, {"uri": ontology_iri})
            except Exception as e:  # noqa: BLE001 pylint: disable=broad-exception-caught
                # Non-fatal; leave duplicates for manual cleanup.
                logger.debug(f"Ontology de-duplication skipped: {e}")

    # ------------------------------------------------------------------
    # Object & Datatype property extraction (missing from original impl)
    # ------------------------------------------------------------------

    def _extract_object_properties(self, g: Graph, ontology_name: str) -> List[Dict[str, Any]]:
        """Extract owl:ObjectProperty triples from RDF graph."""
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for s in g.subjects(RDF.type, OWL.ObjectProperty):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            if uri in seen:
                continue
            seen.add(uri)
            name = (
                self._first_literal(g, s, RDFS.label)
                or self._first_literal(g, s, SKOS.prefLabel)
                or self._local_name(uri)
            )
            domain_uri = next(
                (str(o) for o in g.objects(s, RDFS.domain) if isinstance(o, URIRef)),
                None,
            )
            range_uri = next(
                (str(o) for o in g.objects(s, RDFS.range) if isinstance(o, URIRef)),
                None,
            )
            description = self._first_literal(g, s, RDFS.comment)
            out.append({
                "uri": uri,
                "name": name,
                "domain_uri": domain_uri,
                "range_uri": range_uri,
                "description": description,
                "ontology": ontology_name,
                "ap_level": self.config.ap_level,
                "ap_schema": self.config.ap_schema,
                "ap_standard": self.config.ap_standard,
            })
        return out

    def _extract_datatype_properties(self, g: Graph, ontology_name: str) -> List[Dict[str, Any]]:
        """Extract owl:DatatypeProperty triples from RDF graph."""
        out: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for s in g.subjects(RDF.type, OWL.DatatypeProperty):
            if not isinstance(s, URIRef):
                continue
            uri = str(s)
            if uri in seen:
                continue
            seen.add(uri)
            name = (
                self._first_literal(g, s, RDFS.label)
                or self._first_literal(g, s, SKOS.prefLabel)
                or self._local_name(uri)
            )
            domain_uri = next(
                (str(o) for o in g.objects(s, RDFS.domain) if isinstance(o, URIRef)),
                None,
            )
            range_dt = next(
                (self._local_name(str(o)) for o in g.objects(s, RDFS.range) if isinstance(o, URIRef)),
                None,
            )
            out.append({
                "uri": uri,
                "name": name,
                "domain_uri": domain_uri,
                "range_datatype": range_dt,
                "ontology": ontology_name,
                "ap_level": self.config.ap_level,
                "ap_schema": self.config.ap_schema,
                "ap_standard": self.config.ap_standard,
            })
        return out

    def _upsert_owl_object_properties(self, props: List[Dict[str, Any]]) -> int:
        """Upsert OWLObjectProperty nodes with HAS_OBJECT_PROPERTY + RANGE_CLASS edges."""
        if not props:
            return 0
        node_cypher = """
        UNWIND $rows AS row
        MERGE (op:OWLObjectProperty {uri: row.uri})
        SET op:OWLProperty,
            op.name = row.name,
            op.description = row.description,
            op.ontology = row.ontology,
            op.ap_level = row.ap_level,
            op.ap_schema = row.ap_schema,
            op.ap_standard = row.ap_standard,
            op.owl_type = 'owl:ObjectProperty'
        RETURN count(op) AS count
        """
        # Link domain class → property
        domain_cypher = """
        UNWIND $rows AS row
        MATCH (op:OWLObjectProperty {uri: row.uri})
        MATCH (cls:ExternalOwlClass {uri: row.domain_uri})
        MERGE (cls)-[:HAS_OBJECT_PROPERTY]->(op)
        """
        # Link property → range class
        range_cypher = """
        UNWIND $rows AS row
        MATCH (op:OWLObjectProperty {uri: row.uri})
        MATCH (rng:ExternalOwlClass {uri: row.range_uri})
        MERGE (op)-[:RANGE_CLASS]->(rng)
        """
        total = 0
        with_domain = [r for r in props if r.get("domain_uri")]
        with_range  = [r for r in props if r.get("range_uri")]
        for batch in self._batches(props):
            res = self.neo4j.execute_query(node_cypher, {"rows": batch})
            total += int(res[0]["count"]) if res else 0
        for batch in self._batches(with_domain):
            try:
                self.neo4j.execute_query(domain_cypher, {"rows": batch})
            except Exception as exc:
                logger.warning(f"HAS_OBJECT_PROPERTY batch failed: {exc}")
        for batch in self._batches(with_range):
            try:
                self.neo4j.execute_query(range_cypher, {"rows": batch})
            except Exception as exc:
                logger.warning(f"RANGE_CLASS batch failed: {exc}")
        return total

    def _upsert_owl_datatype_properties(self, props: List[Dict[str, Any]]) -> int:
        """Upsert OWLDatatypeProperty nodes with HAS_DATATYPE_PROPERTY edges."""
        if not props:
            return 0
        node_cypher = """
        UNWIND $rows AS row
        MERGE (dp:OWLDatatypeProperty {uri: row.uri})
        SET dp:OWLProperty,
            dp.name = row.name,
            dp.range_datatype = row.range_datatype,
            dp.ontology = row.ontology,
            dp.ap_level = row.ap_level,
            dp.ap_schema = row.ap_schema,
            dp.ap_standard = row.ap_standard,
            dp.owl_type = 'owl:DatatypeProperty'
        RETURN count(dp) AS count
        """
        domain_cypher = """
        UNWIND $rows AS row
        MATCH (dp:OWLDatatypeProperty {uri: row.uri})
        MATCH (cls:ExternalOwlClass {uri: row.domain_uri})
        MERGE (cls)-[:HAS_DATATYPE_PROPERTY]->(dp)
        """
        total = 0
        with_domain = [r for r in props if r.get("domain_uri")]
        for batch in self._batches(props):
            res = self.neo4j.execute_query(node_cypher, {"rows": batch})
            total += int(res[0]["count"]) if res else 0
        for batch in self._batches(with_domain):
            try:
                self.neo4j.execute_query(domain_cypher, {"rows": batch})
            except Exception as exc:
                logger.warning(f"HAS_DATATYPE_PROPERTY batch failed: {exc}")
        return total

    def _upsert_external_owl_classes(self, classes: List[Dict[str, Any]]) -> int:
        if not classes:
            return 0

        # Add :OWLClass alongside :ExternalOwlClass so the graph API satellite
        # query (which anchors on :OWLClass) picks up these nodes too.
        cypher = """
        UNWIND $rows AS row
        MERGE (c:ExternalOwlClass {uri: row.uri})
        SET c:OWLClass,
            c.name = row.name,
            c.description = row.description,
            c.ontology = row.ontology,
            c.ap_level = row.ap_level,
            c.ap_schema = row.ap_schema,
            c.ap_standard = row.ap_standard
        RETURN count(c) AS count
        """

        total = 0
        for batch in self._batches(classes):
            res = self.neo4j.execute_query(cypher, {"rows": batch})
            total += int(res[0]["count"]) if res else 0
        return total

    def _upsert_class_edges(
        self,
        *,
        rel_type: str,
        edges: List[Tuple[str, str]],
        ontology_name: str,
    ) -> int:
        if not edges:
            return 0

        cypher = f"""
        UNWIND $rows AS row
        MERGE (a:ExternalOwlClass {{uri: row.from_uri}})
        MERGE (b:ExternalOwlClass {{uri: row.to_uri}})
        SET a.ap_level = $ap_level,
            a.ap_schema = $ap_schema,
            a.ap_standard = $ap_standard,
            a.ontology = $ontology,
            b.ap_level = $ap_level,
            b.ap_schema = $ap_schema,
            b.ap_standard = $ap_standard,
            b.ontology = $ontology
        MERGE (a)-[r:{rel_type}]->(b)
        SET r.ap_level = $ap_level,
            r.ap_schema = $ap_schema,
            r.ap_standard = $ap_standard
        RETURN count(r) AS count
        """

        rows = [{"from_uri": a, "to_uri": b} for a, b in edges]

        total = 0
        for batch in self._batches(rows):
            res = self.neo4j.execute_query(
                cypher,
                {
                    "rows": batch,
                    "ap_level": self.config.ap_level,
                    "ap_schema": self.config.ap_schema,
                    "ap_standard": self.config.ap_standard,
                    "ontology": ontology_name,
                },
            )
            total += int(res[0]["count"]) if res else 0
        return total

    def _upsert_external_units(self, units: List[Dict[str, Any]]) -> int:
        if not units:
            return 0

        cypher = """
        UNWIND $rows AS row
        MERGE (u:ExternalUnit {uri: row.uri})
        SET u.name = row.name,
            u.symbol = row.symbol,
            u.unit_type = row.unit_type,
            u.si_conversion = row.si_conversion,
            u.ontology = row.ontology,
            u.ap_level = row.ap_level,
            u.ap_schema = row.ap_schema,
            u.ap_standard = row.ap_standard
        RETURN count(u) AS count
        """

        total = 0
        for batch in self._batches(units):
            res = self.neo4j.execute_query(cypher, {"rows": batch})
            total += int(res[0]["count"]) if res else 0
        return total

    def _upsert_value_types(self, value_types: List[Dict[str, Any]]) -> int:
        if not value_types:
            return 0

        cypher = """
        UNWIND $rows AS row
        MERGE (vt:ValueType {uri: row.uri})
        SET vt.name = row.name,
            vt.data_type = row.data_type,
            vt.unit_reference = row.unit_reference,
            vt.ontology = row.ontology,
            vt.ap_level = row.ap_level,
            vt.ap_schema = row.ap_schema,
            vt.ap_standard = row.ap_standard
        RETURN count(vt) AS count
        """

        total = 0
        for batch in self._batches(value_types):
            res = self.neo4j.execute_query(cypher, {"rows": batch})
            total += int(res[0]["count"]) if res else 0
        return total

    def _upsert_classifications(self, classifications: List[Dict[str, Any]]) -> int:
        if not classifications:
            return 0

        cypher = """
        UNWIND $rows AS row
        MERGE (c:Classification {uri: row.uri})
        SET c.name = row.name,
            c.classification_system = row.classification_system,
            c.code = row.code,
            c.ontology = row.ontology,
            c.ap_level = row.ap_level,
            c.ap_schema = row.ap_schema,
            c.ap_standard = row.ap_standard
        RETURN count(c) AS count
        """

        total = 0
        for batch in self._batches(classifications):
            res = self.neo4j.execute_query(cypher, {"rows": batch})
            total += int(res[0]["count"]) if res else 0
        return total

    def _link_resources_to_ontology(self, ontology_name: str) -> None:
        # Relationship linking based on stored `ontology` property.
        cypher = """
        MATCH (o:ExternalOntology {name: $name})
        WITH o
        MATCH (n)
        WHERE n.ontology = $name AND n.ap_level = $ap_level
        MERGE (o)-[:DEFINES_REFERENCE_DATA]->(n)
        """
        try:
            self.neo4j.execute_query(
                cypher,
                {"name": ontology_name, "ap_level": self.config.ap_level},
            )
        except Exception as e:  # noqa: BLE001 pylint: disable=broad-exception-caught
            logger.warning(f"Failed linking resources to ontology node: {e}")

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _batches(self, rows: List[Dict[str, Any]]) -> Iterable[List[Dict[str, Any]]]:
        bs = max(1, int(self.config.batch_size))
        for i in range(0, len(rows), bs):
            yield rows[i : i + bs]

    def _first_literal(self, g: Graph, s: Any, p: Any) -> Optional[str]:
        for o in g.objects(s, p):
            if isinstance(o, Literal):
                text = str(o).strip()
                if text:
                    return text
        return None

    def _local_name(self, uri: str) -> str:
        # Handle both '#' and '/' namespaces
        if "#" in uri:
            return uri.rsplit("#", 1)[-1]
        return uri.rstrip("/").rsplit("/", 1)[-1]
