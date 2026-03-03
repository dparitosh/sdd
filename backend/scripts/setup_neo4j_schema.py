#!/usr/bin/env python3
"""Neo4j schema setup: constraints, indexes & full-text indexes.

Usage:
    python backend/scripts/setup_neo4j_schema.py

Pre-conditions:
    - Neo4j 5+ running with the ``mossec`` database created
    - Env vars: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD (or defaults below)

Actions:
    1. Create unique constraints on uid / uri columns.
    2. Create property indexes for common lookups.
    3. Create full-text indexes for search (plmxml_fulltext, ontology_fulltext).
    4. Verify with SHOW INDEXES.
"""

from __future__ import annotations

import os
import sys

from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "mossec")


def _run(tx, cypher: str) -> None:
    """Execute a single DDL statement inside a transaction."""
    tx.run(cypher)


# ------------------------------------------------------------------
# 1. Unique constraints
# ------------------------------------------------------------------

UNIQUE_CONSTRAINTS: list[tuple[str, str, str]] = [
    # (constraint_name, label, property)
    ("uq_plmxml_item_uid",      "PLMXMLItem",          "uid"),
    ("uq_plmxml_revision_uid",  "PLMXMLRevision",      "uid"),
    ("uq_plmxml_bomline_uid",   "PLMXMLBOMLine",       "uid"),
    ("uq_plmxml_dataset_uid",   "PLMXMLDataSet",       "uid"),
    ("uq_step_file_uid",        "StepFile",            "uid"),
    ("uq_owl_class_uri",        "ExternalOwlClass",    "uri"),
    ("uq_shacl_violation_uid",  "SHACLViolation",      "uid"),
]


def create_unique_constraints(session) -> None:
    print("=" * 60)
    print("1. Creating unique constraints …")
    print("=" * 60)
    for name, label, prop in UNIQUE_CONSTRAINTS:
        cypher = (
            f"CREATE CONSTRAINT {name} IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
        )
        try:
            session.execute_write(_run, cypher)
            print(f"   ✓ {name}  ({label}.{prop})")
        except Exception as exc:  # noqa: BLE001
            print(f"   ✗ {name}  — {exc}")
    print()


# ------------------------------------------------------------------
# 2. Property indexes
# ------------------------------------------------------------------

PROPERTY_INDEXES: list[tuple[str, str, list[str]]] = [
    # (index_name, label, [properties])
    ("idx_plmxml_item_type",      "PLMXMLItem",       ["item_type"]),
    ("idx_plmxml_item_name",      "PLMXMLItem",       ["name"]),
    ("idx_owl_class_name",        "ExternalOwlClass", ["name"]),
    ("idx_owl_class_ap_level",    "ExternalOwlClass", ["ap_level"]),
    ("idx_shacl_target_uid",      "SHACLViolation",   ["target_uid"]),
]


def create_property_indexes(session) -> None:
    print("=" * 60)
    print("2. Creating property indexes …")
    print("=" * 60)
    for name, label, props in PROPERTY_INDEXES:
        prop_str = ", ".join(f"n.{p}" for p in props)
        cypher = (
            f"CREATE INDEX {name} IF NOT EXISTS "
            f"FOR (n:{label}) ON ({prop_str})"
        )
        try:
            session.execute_write(_run, cypher)
            print(f"   ✓ {name}  ({label} → {', '.join(props)})")
        except Exception as exc:  # noqa: BLE001
            print(f"   ✗ {name}  — {exc}")
    print()


# ------------------------------------------------------------------
# 3. Full-text indexes
# ------------------------------------------------------------------

FULLTEXT_INDEXES: list[tuple[str, list[str], list[str]]] = [
    # (index_name, [labels], [properties])
    (
        "plmxml_fulltext",
        ["PLMXMLItem", "PLMXMLRevision", "PLMXMLDataSet"],
        ["name"],
    ),
    (
        "ontology_fulltext",
        ["ExternalOwlClass", "OWLProperty"],
        ["name", "description"],
    ),
]


def create_fulltext_indexes(session) -> None:
    print("=" * 60)
    print("3. Creating full-text indexes …")
    print("=" * 60)
    for name, labels, props in FULLTEXT_INDEXES:
        labels_str = ", ".join(labels)
        props_str = ", ".join(f"n.{p}" for p in props)
        cypher = (
            f"CREATE FULLTEXT INDEX {name} IF NOT EXISTS "
            f"FOR (n:{labels_str}) ON EACH [{props_str}]"
        )
        try:
            session.execute_write(_run, cypher)
            print(f"   ✓ {name}  ({labels_str} → {', '.join(props)})")
        except Exception as exc:  # noqa: BLE001
            print(f"   ✗ {name}  — {exc}")
    print()


# ------------------------------------------------------------------
# 4. Verify
# ------------------------------------------------------------------

def verify_indexes(session) -> None:
    print("=" * 60)
    print("4. Verifying indexes (SHOW INDEXES) …")
    print("=" * 60)
    result = session.run("SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state")
    rows = list(result)
    if not rows:
        print("   No indexes found.")
        return
    # Header
    print(f"   {'Name':<30} {'Type':<15} {'Labels':<40} {'Properties':<25} {'State'}")
    print(f"   {'-'*30} {'-'*15} {'-'*40} {'-'*25} {'-'*10}")
    for record in rows:
        name = record["name"]
        idx_type = record["type"]
        labels = ", ".join(record["labelsOrTypes"] or [])
        props = ", ".join(record["properties"] or [])
        state = record["state"]
        print(f"   {name:<30} {idx_type:<15} {labels:<40} {props:<25} {state}")
    print(f"\n   Total indexes: {len(rows)}\n")


# ------------------------------------------------------------------
# 5. Show constraint summary
# ------------------------------------------------------------------

def verify_constraints(session) -> None:
    print("=" * 60)
    print("5. Verifying constraints (SHOW CONSTRAINTS) …")
    print("=" * 60)
    result = session.run("SHOW CONSTRAINTS YIELD name, type, labelsOrTypes, properties")
    rows = list(result)
    if not rows:
        print("   No constraints found.")
        return
    print(f"   {'Name':<35} {'Type':<20} {'Labels':<25} {'Properties'}")
    print(f"   {'-'*35} {'-'*20} {'-'*25} {'-'*20}")
    for record in rows:
        name = record["name"]
        c_type = record["type"]
        labels = ", ".join(record["labelsOrTypes"] or [])
        props = ", ".join(record["properties"] or [])
        print(f"   {name:<35} {c_type:<20} {labels:<25} {props}")
    print(f"\n   Total constraints: {len(rows)}\n")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    print(f"\nConnecting to Neo4j: {NEO4J_URI}  db={NEO4J_DATABASE}\n")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        driver.verify_connectivity()
    except Exception as exc:
        print(f"ERROR: Cannot connect to Neo4j at {NEO4J_URI}")
        print(f"       {exc}")
        print("Make sure Neo4j is running and env vars are correct.")
        sys.exit(1)

    with driver.session(database=NEO4J_DATABASE) as session:
        create_unique_constraints(session)
        create_property_indexes(session)
        create_fulltext_indexes(session)
        verify_indexes(session)
        verify_constraints(session)

    driver.close()
    print("Done — Neo4j schema setup complete.\n")


if __name__ == "__main__":
    main()
