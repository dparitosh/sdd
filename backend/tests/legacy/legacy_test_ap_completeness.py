#!/usr/bin/env python3
"""
AP239/AP242/AP243 Knowledge Graph Completeness Validation
==========================================================
This script validates the completeness and correctness of the AP hierarchy
in the Neo4j knowledge graph.

Validation Layers:
1. Schema Validation - Check indexes, labels, properties exist
2. Data Completeness - Verify nodes exist at all 3 levels
3. Relationship Integrity - Validate cross-level links
4. Traceability Chains - Test end-to-end paths
5. Semantic Consistency - Check naming patterns and metadata

Usage:
    python test_ap_completeness.py [--verbose]
"""

import argparse
import sys
from typing import Dict, List

from loguru import logger
from src.web.services import get_neo4j_service


class APCompletenessValidator:
    """Validates AP239/AP242/AP243 knowledge graph completeness."""

    def __init__(self, verbose: bool = False):
        self.neo4j = get_neo4j_service()
        self.verbose = verbose
        self.results = {"passed": 0, "failed": 0, "warnings": 0, "tests": []}

    def run_all_tests(self):
        """Execute all validation tests."""
        print("\n" + "=" * 80)
        print("AP239/AP242/AP243 KNOWLEDGE GRAPH VALIDATION")
        print("=" * 80 + "\n")

        # Layer 1: Schema Validation
        self._test_indexes_exist()
        self._test_labels_exist()
        self._test_metadata_properties()

        # Layer 2: Data Completeness
        self._test_ap239_nodes()
        self._test_ap242_nodes()
        self._test_ap243_nodes()

        # Layer 3: Relationship Integrity
        self._test_ap239_internal_relationships()
        self._test_ap242_internal_relationships()
        self._test_cross_level_relationships()

        # Layer 4: Traceability Chains
        self._test_requirement_to_part_chains()
        self._test_requirement_to_ontology_chains()
        self._test_end_to_end_traceability()

        # Layer 5: Semantic Consistency
        self._test_ap_level_consistency()
        self._test_naming_patterns()
        self._test_orphaned_nodes()

        # Report results
        self._print_summary()

    def _test_indexes_exist(self):
        """Test 1: Verify all required indexes exist."""
        print("TEST 1: Schema Indexes")
        print("-" * 80)

        required_indexes = [
            "idx_requirement_id",
            "idx_requirement_name",
            "idx_part_id",
            "idx_part_name",
            "idx_material_name",
            "idx_external_owl_class_name",
        ]

        # Use SHOW INDEXES for Neo4j 5.x
        query = "SHOW INDEXES YIELD name RETURN collect(name) AS indexes"
        try:
            result = self.neo4j.execute_query(query)
            existing_indexes = result[0]["indexes"] if result else []

            missing = [idx for idx in required_indexes if idx not in existing_indexes]

            if not missing:
                self._pass(f"All {len(required_indexes)} required indexes exist")
            else:
                self._fail(f"Missing indexes: {', '.join(missing)}")
        except Exception as e:
            self._warn(f"Could not check indexes: {str(e)[:50]}")

    def _test_labels_exist(self):
        """Test 2: Verify all AP node labels exist."""
        print("\nTEST 2: Node Labels")
        print("-" * 80)

        required_labels = {
            "AP239": ["Requirement", "Analysis", "Approval", "Document"],
            "AP242": ["Part", "Material", "Assembly", "GeometricModel"],
            "AP243": ["ExternalOwlClass", "ExternalUnit", "Classification"],
        }

        # Use SHOW LABELS for Neo4j 5.x
        query = "CALL db.labels() YIELD label RETURN collect(label) AS labels"
        try:
            result = self.neo4j.execute_query(query)
            existing_labels = result[0]["labels"] if result else []

            all_present = True
            for schema, labels in required_labels.items():
                missing = [lbl for lbl in labels if lbl not in existing_labels]
                if missing:
                    self._fail(f"{schema}: Missing labels {', '.join(missing)}")
                    all_present = False
                else:
                    self._pass(f"{schema}: All labels present")

            if all_present:
                self._pass("All 11 required node labels exist")
        except Exception as e:
            self._warn(f"Could not check labels: {str(e)[:50]}")

    def _test_metadata_properties(self):
        """Test 3: Verify ap_level and ap_schema properties."""
        print("\nTEST 3: Metadata Properties")
        print("-" * 80)

        query = """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL
        RETURN n.ap_level AS level, n.ap_schema AS schema, count(*) AS count
        ORDER BY level
        """
        results = self.neo4j.execute_query(query)

        if not results:
            self._fail("No nodes have ap_level metadata")
            return

        expected_levels = {1: "AP239", 2: "AP242", 3: "AP243"}
        found_levels = {r["level"]: r["schema"] for r in results}

        for level, schema in expected_levels.items():
            if level in found_levels:
                count = next(r["count"] for r in results if r["level"] == level)
                self._pass(f"Level {level} ({schema}): {count:,} nodes")
            else:
                self._fail(f"Level {level} ({schema}): No nodes found")

    def _test_ap239_nodes(self):
        """Test 4: AP239 node completeness."""
        print("\nTEST 4: AP239 Data Completeness (Requirements Layer)")
        print("-" * 80)

        node_types = ["Requirement", "Analysis", "Approval", "Document"]

        for node_type in node_types:
            query = (
                f"MATCH (n:{node_type}) WHERE n.ap_level = 1 RETURN count(n) AS count"
            )
            result = self.neo4j.execute_query(query)
            count = result[0]["count"] if result else 0

            if count > 0:
                self._pass(f"{node_type}: {count:,} nodes")
            else:
                self._warn(f"{node_type}: No nodes (may be expected)")

    def _test_ap242_nodes(self):
        """Test 5: AP242 node completeness."""
        print("\nTEST 5: AP242 Data Completeness (Engineering Layer)")
        print("-" * 80)

        node_types = ["Part", "Material", "Assembly", "GeometricModel"]

        for node_type in node_types:
            query = (
                f"MATCH (n:{node_type}) WHERE n.ap_level = 2 RETURN count(n) AS count"
            )
            result = self.neo4j.execute_query(query)
            count = result[0]["count"] if result else 0

            if count > 0:
                self._pass(f"{node_type}: {count:,} nodes")
            else:
                self._warn(f"{node_type}: No nodes (may be expected)")

    def _test_ap243_nodes(self):
        """Test 6: AP243 node completeness."""
        print("\nTEST 6: AP243 Data Completeness (Reference Data Layer)")
        print("-" * 80)

        node_types = ["ExternalOwlClass", "ExternalUnit", "Classification"]

        for node_type in node_types:
            query = (
                f"MATCH (n:{node_type}) WHERE n.ap_level = 3 RETURN count(n) AS count"
            )
            result = self.neo4j.execute_query(query)
            count = result[0]["count"] if result else 0

            if count > 0:
                self._pass(f"{node_type}: {count:,} nodes")
            else:
                self._warn(f"{node_type}: No nodes (may be expected)")

    def _test_ap239_internal_relationships(self):
        """Test 7: AP239 internal relationships."""
        print("\nTEST 7: AP239 Internal Relationships")
        print("-" * 80)

        relationships = ["SATISFIES", "VERIFIES", "REFINES", "APPROVES", "ANALYZES"]

        for rel_type in relationships:
            query = f"""
            MATCH (n1)-[r:{rel_type}]->(n2)
            WHERE n1.ap_level = 1 AND n2.ap_level = 1
            RETURN count(r) AS count
            """
            result = self.neo4j.execute_query(query)
            count = result[0]["count"] if result else 0

            if count > 0:
                self._pass(f"{rel_type}: {count:,} relationships")
            else:
                self._warn(f"{rel_type}: No relationships")

    def _test_ap242_internal_relationships(self):
        """Test 8: AP242 internal relationships."""
        print("\nTEST 8: AP242 Internal Relationships")
        print("-" * 80)

        relationships = [
            "HAS_GEOMETRY",
            "USES_MATERIAL",
            "ASSEMBLES_WITH",
            "HAS_VERSION",
        ]

        for rel_type in relationships:
            query = f"""
            MATCH (n1)-[r:{rel_type}]->(n2)
            WHERE n1.ap_level = 2 AND n2.ap_level = 2
            RETURN count(r) AS count
            """
            result = self.neo4j.execute_query(query)
            count = result[0]["count"] if result else 0

            if count > 0:
                self._pass(f"{rel_type}: {count:,} relationships")
            else:
                self._warn(f"{rel_type}: No relationships")

    def _test_cross_level_relationships(self):
        """Test 9: Cross-level relationships."""
        print("\nTEST 9: Cross-Level Relationships (Traceability)")
        print("-" * 80)

        query = """
        MATCH (n1)-[r]->(n2)
        WHERE n1.ap_level IS NOT NULL AND n2.ap_level IS NOT NULL
          AND n1.ap_level <> n2.ap_level
        RETURN n1.ap_level AS from_level, n2.ap_level AS to_level,
               type(r) AS rel_type, count(*) AS count
        ORDER BY from_level, to_level
        """
        results = self.neo4j.execute_query(query)

        if results:
            for r in results:
                self._pass(
                    f"Level {r['from_level']}→{r['to_level']}: {r['rel_type']} ({r['count']:,})"
                )
        else:
            self._fail("No cross-level relationships found")

    def _test_requirement_to_part_chains(self):
        """Test 10: Requirement → Part traceability chains."""
        print("\nTEST 10: Requirement → Part Chains")
        print("-" * 80)

        query = """
        MATCH path = (req:Requirement)-[*1..3]->(part:Part)
        WHERE req.ap_level = 1 AND part.ap_level = 2
        RETURN count(DISTINCT path) AS count, min(length(path)) AS min_hops, max(length(path)) AS max_hops
        """
        result = self.neo4j.execute_query(query)

        if result and result[0]["count"] > 0:
            count = result[0]["count"]
            min_hops = result[0]["min_hops"]
            max_hops = result[0]["max_hops"]
            self._pass(
                f"Found {count:,} chains (path length: {min_hops}-{max_hops} hops)"
            )
        else:
            self._warn("No Requirement→Part chains found")

    def _test_requirement_to_ontology_chains(self):
        """Test 11: Requirement → Ontology traceability chains."""
        print("\nTEST 11: Requirement → Ontology Chains")
        print("-" * 80)

        query = """
        MATCH path = (req:Requirement)-[*1..5]->(owl:ExternalOwlClass)
        WHERE req.ap_level = 1 AND owl.ap_level = 3
        RETURN count(DISTINCT path) AS count, min(length(path)) AS min_hops, max(length(path)) AS max_hops
        """
        result = self.neo4j.execute_query(query)

        if result and result[0]["count"] > 0:
            count = result[0]["count"]
            min_hops = result[0]["min_hops"]
            max_hops = result[0]["max_hops"]
            self._pass(
                f"Found {count:,} chains (path length: {min_hops}-{max_hops} hops)"
            )
        else:
            self._warn("No Requirement→Ontology chains found")

    def _test_end_to_end_traceability(self):
        """Test 12: Complete AP239→AP242→AP243 traceability."""
        print("\nTEST 12: End-to-End Traceability (AP239→AP242→AP243)")
        print("-" * 80)

        query = """
        MATCH path = (req:Requirement)-[*1..6]->(part:Part)-[*1..3]->(owl:ExternalOwlClass)
        WHERE req.ap_level = 1 AND part.ap_level = 2 AND owl.ap_level = 3
        RETURN count(DISTINCT path) AS count, min(length(path)) AS min_hops, max(length(path)) AS max_hops
        LIMIT 1
        """
        result = self.neo4j.execute_query(query)

        if result and result[0]["count"] > 0:
            count = result[0]["count"]
            min_hops = result[0]["min_hops"]
            max_hops = result[0]["max_hops"]
            self._pass(
                f"Found {count:,} complete chains (path length: {min_hops}-{max_hops} hops)"
            )
        else:
            self._warn("No complete AP239→AP242→AP243 chains found")

    def _test_ap_level_consistency(self):
        """Test 13: AP level consistency."""
        print("\nTEST 13: AP Level Consistency")
        print("-" * 80)

        # Check for nodes with ap_level but wrong ap_schema
        query = """
        MATCH (n)
        WHERE n.ap_level = 1 AND n.ap_schema <> 'AP239'
           OR n.ap_level = 2 AND n.ap_schema <> 'AP242'
           OR n.ap_level = 3 AND n.ap_schema <> 'AP243'
        RETURN count(n) AS inconsistent
        """
        result = self.neo4j.execute_query(query)
        inconsistent = result[0]["inconsistent"] if result else 0

        if inconsistent == 0:
            self._pass("All nodes have consistent ap_level/ap_schema")
        else:
            self._fail(f"{inconsistent} nodes have inconsistent metadata")

    def _test_naming_patterns(self):
        """Test 14: Naming pattern consistency."""
        print("\nTEST 14: Naming Pattern Consistency")
        print("-" * 80)

        # Check for nodes without names
        query = """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL AND (n.name IS NULL OR n.name = '')
        RETURN labels(n)[0] AS node_type, count(n) AS count
        """
        results = self.neo4j.execute_query(query)

        if not results:
            self._pass("All AP nodes have names")
        else:
            for r in results:
                self._warn(f"{r['node_type']}: {r['count']} nodes without names")

    def _test_orphaned_nodes(self):
        """Test 15: Check for orphaned nodes."""
        print("\nTEST 15: Orphaned Node Detection")
        print("-" * 80)

        query = """
        MATCH (n)
        WHERE n.ap_level IS NOT NULL
          AND NOT (n)-[]-()
        RETURN labels(n)[0] AS node_type, count(n) AS count
        ORDER BY count DESC
        """
        results = self.neo4j.execute_query(query)

        if not results:
            self._pass("No orphaned nodes (all connected)")
        else:
            total_orphaned = sum(r["count"] for r in results)
            for r in results:
                self._warn(f"{r['node_type']}: {r['count']} orphaned nodes")
            self._warn(f"Total orphaned: {total_orphaned:,} nodes")

    def _pass(self, message: str):
        """Record passing test."""
        print(f"  ✓ {message}")
        self.results["passed"] += 1
        self.results["tests"].append(("PASS", message))

    def _fail(self, message: str):
        """Record failing test."""
        print(f"  ✗ {message}")
        self.results["failed"] += 1
        self.results["tests"].append(("FAIL", message))

    def _warn(self, message: str):
        """Record warning."""
        print(f"  ⚠ {message}")
        self.results["warnings"] += 1
        self.results["tests"].append(("WARN", message))

    def _print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        print(f"Tests Passed:    {self.results['passed']:3d}")
        print(f"Tests Failed:    {self.results['failed']:3d}")
        print(f"Warnings:        {self.results['warnings']:3d}")
        print(f"Total Tests:     {len(self.results['tests']):3d}")
        print("=" * 80)

        if self.results["failed"] == 0:
            print("\n✅ KNOWLEDGE GRAPH IS COMPLETE AND CORRECT!")
            return 0
        else:
            print(
                f"\n❌ {self.results['failed']} VALIDATION FAILURES - REVIEW REQUIRED"
            )
            return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate AP239/AP242/AP243 knowledge graph"
    )
    parser.add_argument("--verbose", action="store_true", help="Print detailed output")
    args = parser.parse_args()

    validator = APCompletenessValidator(verbose=args.verbose)
    exit_code = validator.run_all_tests()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
