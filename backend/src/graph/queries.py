"""Pre-built Cypher queries for common MBSE patterns.

All queries that accept user input use *parameterized* queries ($param syntax)
instead of f-string interpolation to prevent Cypher injection.
"""

from typing import Any, Dict, List, Tuple


class GraphQueries:
    """Collection of useful Cypher queries for MBSE knowledge graphs.

    Methods that accept user input return ``(query_string, params_dict)``
    tuples suitable for ``session.run(query, params)``.
    """

    @staticmethod
    def find_all_systems() -> str:
        """Query to find all system nodes"""
        return "MATCH (s:System) RETURN s"

    @staticmethod
    def find_system_components(system_id: str) -> Tuple[str, Dict[str, Any]]:
        """Query to find all components of a system"""
        return (
            "MATCH (s:System {id: $system_id})-[:HAS_COMPONENT]->(c:Component) RETURN c",
            {"system_id": system_id},
        )

    @staticmethod
    def find_requirements_for_component(component_id: str) -> Tuple[str, Dict[str, Any]]:
        """Query to find requirements satisfied by a component"""
        return (
            "MATCH (c:Component {id: $component_id})-[:SATISFIES]->(r:Requirement) RETURN r",
            {"component_id": component_id},
        )

    @staticmethod
    def find_connected_interfaces(component_id: str) -> Tuple[str, Dict[str, Any]]:
        """Query to find interfaces connected to a component"""
        return (
            "MATCH (c:Component {id: $component_id})-[:HAS_INTERFACE]->(i:Interface) RETURN i",
            {"component_id": component_id},
        )

    @staticmethod
    def get_system_hierarchy() -> str:
        """Query to get complete system hierarchy"""
        return """
        MATCH path = (s:System)-[:HAS_COMPONENT*]->(c:Component)
        RETURN path
        """

    @staticmethod
    def find_orphaned_components() -> str:
        """Query to find components not connected to any system"""
        return """
        MATCH (c:Component)
        WHERE NOT (c)<-[:HAS_COMPONENT]-(:System)
        RETURN c
        """

    @staticmethod
    def get_graph_statistics() -> str:
        """Query to get graph statistics"""
        return """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
