"""
OSLC Seed Data Loader
Loads OSLC Core and RM vocabulary definitions from Turtle files into Neo4j
as OntologyClass / OntologyProperty nodes so the Knowledge Graph is
self-describing with respect to the OSLC standards it supports.

Usage:
    python -m backend.scripts.load_oslc_seed
    # or
    python backend/scripts/load_oslc_seed.py
"""

import os
import sys

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rdflib import Graph, RDF, RDFS, OWL
from rdflib.namespace import DCTERMS
from loguru import logger

from src.web.services import get_neo4j_service

SEED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "seed", "oslc")


def load_turtle_file(filepath: str) -> Graph:
    """Parse a Turtle file into an RDFLib Graph."""
    g = Graph()
    g.parse(filepath, format="turtle")
    logger.info(f"Parsed {filepath}: {len(g)} triples")
    return g


def ingest_graph(neo4j, g: Graph, source_label: str):
    """
    Walk an RDFLib graph and upsert vocabulary terms into Neo4j.
    - rdfs:Class  → :OntologyClass node
    - rdf:Property → :OntologyProperty node
    - owl:Ontology → :Ontology node (metadata)
    """
    stats = {"classes": 0, "properties": 0, "ontologies": 0}

    for subj in g.subjects(RDF.type, OWL.Ontology):
        title = str(g.value(subj, DCTERMS.title) or str(subj))
        desc = str(g.value(subj, DCTERMS.description) or "")
        neo4j.execute_query(
            """
            MERGE (o:Ontology {uri: $uri})
            SET o.title = $title,
                o.description = $desc,
                o.source = $source
            """,
            {"uri": str(subj), "title": title, "desc": desc, "source": source_label},
        )
        stats["ontologies"] += 1

    for subj in g.subjects(RDF.type, RDFS.Class):
        label = str(g.value(subj, RDFS.label) or str(subj).split("#")[-1].split("/")[-1])
        comment = str(g.value(subj, RDFS.comment) or "")
        defined_by = str(g.value(subj, RDFS.isDefinedBy) or "")
        neo4j.execute_query(
            """
            MERGE (c:OntologyClass {uri: $uri})
            SET c.label = $label,
                c.comment = $comment,
                c.definedBy = $defined_by,
                c.source = $source
            """,
            {
                "uri": str(subj),
                "label": label,
                "comment": comment,
                "defined_by": defined_by,
                "source": source_label,
            },
        )
        stats["classes"] += 1

    for subj in g.subjects(RDF.type, RDF.Property):
        label = str(g.value(subj, RDFS.label) or str(subj).split("#")[-1].split("/")[-1])
        comment = str(g.value(subj, RDFS.comment) or "")
        defined_by = str(g.value(subj, RDFS.isDefinedBy) or "")
        neo4j.execute_query(
            """
            MERGE (p:OntologyProperty {uri: $uri})
            SET p.label = $label,
                p.comment = $comment,
                p.definedBy = $defined_by,
                p.source = $source
            """,
            {
                "uri": str(subj),
                "label": label,
                "comment": comment,
                "defined_by": defined_by,
                "source": source_label,
            },
        )
        stats["properties"] += 1

    return stats


def main():
    neo4j = get_neo4j_service()
    total = {"classes": 0, "properties": 0, "ontologies": 0}

    for filename in sorted(os.listdir(SEED_DIR)):
        if not filename.endswith(".ttl"):
            continue
        filepath = os.path.join(SEED_DIR, filename)
        g = load_turtle_file(filepath)
        stats = ingest_graph(neo4j, g, source_label=filename)
        logger.info(f"  {filename}: {stats}")
        for k in total:
            total[k] += stats[k]

    logger.info(f"OSLC seed load complete: {total}")


if __name__ == "__main__":
    main()
