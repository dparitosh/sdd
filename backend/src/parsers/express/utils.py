"""
EXPRESS Parser Utilities
============================================================================
Helper functions for EXPRESS schema analysis, conversion, and Neo4j integration.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from datetime import datetime

from .models import (
    ExpressSchema,
    ExpressEntity,
    ExpressType,
    ExpressAttribute,
)


class ExpressAnalyzer:
    """
    Analysis utilities for EXPRESS schemas.
    Provides inheritance mapping, dependency analysis, and statistics.
    """
    
    @staticmethod
    def get_inheritance_tree(schema: ExpressSchema, root_entity: Optional[str] = None) -> Dict[str, Any]:
        """
        Build inheritance tree for entities.
        
        Args:
            schema: The EXPRESS schema to analyze
            root_entity: Optional root entity to start from (None = all roots)
            
        Returns:
            Dictionary representing the inheritance hierarchy
        """
        # Build child -> parent mapping
        parent_map = {
            name: entity.supertype
            for name, entity in schema.entities.items()
            if entity.supertype
        }
        
        # Build parent -> children mapping
        children_map: Dict[str, List[str]] = {}
        for child, parent in parent_map.items():
            if parent not in children_map:
                children_map[parent] = []
            children_map[parent].append(child)
        
        def build_tree(entity_name: str) -> Dict[str, Any]:
            entity = schema.entities.get(entity_name)
            children = children_map.get(entity_name, [])
            return {
                "name": entity_name,
                "is_abstract": entity.is_abstract if entity else False,
                "attribute_count": len(entity.attributes) if entity else 0,
                "children": [build_tree(child) for child in sorted(children)]
            }
        
        if root_entity:
            return build_tree(root_entity)
        
        # Find all root entities (no supertype)
        roots = [
            name for name, entity in schema.entities.items()
            if not entity.supertype
        ]
        
        return {
            "schema": schema.name,
            "roots": [build_tree(root) for root in sorted(roots)]
        }
    
    @staticmethod
    def get_type_references(schema: ExpressSchema, type_name: str) -> List[str]:
        """
        Find all entities that reference a specific type.
        
        Args:
            schema: The EXPRESS schema
            type_name: Type name to search for
            
        Returns:
            List of entity names that use this type
        """
        referencing_entities = []
        
        for entity_name, entity in schema.entities.items():
            for attr in entity.attributes:
                if type_name.lower() in attr.type_ref.lower():
                    referencing_entities.append(entity_name)
                    break
        
        return referencing_entities
    
    @staticmethod
    def get_select_type_usage(schema: ExpressSchema) -> Dict[str, List[str]]:
        """
        Map SELECT types to where they're used.
        
        Returns:
            Dict mapping select type name to list of using entities
        """
        select_types = {
            name for name, t in schema.types.items()
            if t.is_select
        }
        
        usage = {st: [] for st in select_types}
        
        for entity_name, entity in schema.entities.items():
            for attr in entity.attributes:
                for select_type in select_types:
                    if select_type.lower() in attr.type_ref.lower():
                        usage[select_type].append(entity_name)
        
        return usage
    
    @staticmethod
    def get_schema_statistics(schema: ExpressSchema) -> Dict[str, Any]:
        """
        Generate comprehensive statistics for a schema.
        
        Returns:
            Dictionary with various metrics
        """
        # Count entity characteristics
        abstract_entities = sum(1 for e in schema.entities.values() if e.is_abstract)
        entities_with_inheritance = sum(1 for e in schema.entities.values() if e.supertype)
        
        # Count attribute characteristics
        total_attributes = sum(len(e.attributes) for e in schema.entities.values())
        optional_attributes = sum(
            sum(1 for a in e.attributes if a.optional)
            for e in schema.entities.values()
        )
        list_attributes = sum(
            sum(1 for a in e.attributes if a.is_list)
            for e in schema.entities.values()
        )
        
        # Count type characteristics
        select_types = sum(1 for t in schema.types.values() if t.is_select)
        enum_types = sum(1 for t in schema.types.values() if t.is_enumeration)
        
        return {
            "schema_name": schema.name,
            "source_file": schema.source_file,
            "parsed_at": schema.parsed_at.isoformat() if schema.parsed_at else None,
            "entities": {
                "total": len(schema.entities),
                "abstract": abstract_entities,
                "concrete": len(schema.entities) - abstract_entities,
                "with_inheritance": entities_with_inheritance,
            },
            "types": {
                "total": len(schema.types),
                "select": select_types,
                "enumeration": enum_types,
                "other": len(schema.types) - select_types - enum_types,
            },
            "attributes": {
                "total": total_attributes,
                "optional": optional_attributes,
                "required": total_attributes - optional_attributes,
                "collections": list_attributes,
            },
            "imports": len(schema.imports),
            "functions": len(schema.functions),
            "rules": len(schema.rules),
        }
    
    @staticmethod
    def find_circular_dependencies(schemas: Dict[str, ExpressSchema]) -> List[List[str]]:
        """
        Find circular import dependencies between schemas.
        
        Args:
            schemas: Dictionary of schema name to schema
            
        Returns:
            List of circular dependency chains
        """
        # Build import graph
        graph: Dict[str, Set[str]] = {}
        for name, schema in schemas.items():
            graph[name] = {imp.schema_name for imp in schema.imports}
        
        # Find cycles using DFS
        cycles = []
        visited = set()
        rec_stack = []
        
        def dfs(node: str, path: List[str]):
            if node in path:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, set()):
                dfs(neighbor, path.copy())
        
        for node in graph:
            dfs(node, [])
        
        return cycles


class ExpressNeo4jConverter:
    """
    Convert EXPRESS schemas to Neo4j-compatible structures.
    """
    
    @staticmethod
    def schema_to_cypher(
        schema: ExpressSchema,
        label_prefix: str = "",
        include_relationships: bool = True
    ) -> List[str]:
        """
        Generate Cypher statements to create schema in Neo4j.
        
        Args:
            schema: The EXPRESS schema
            label_prefix: Optional prefix for node labels (e.g., "AP239_")
            include_relationships: Whether to include relationship statements
            
        Returns:
            List of Cypher statements
        """
        statements = []
        
        # Create schema node
        schema_props = json.dumps({
            "name": schema.name,
            "source_file": schema.source_file,
            "entity_count": len(schema.entities),
            "type_count": len(schema.types),
            "import_count": len(schema.imports),
        })
        statements.append(
            f"MERGE (s:{label_prefix}Schema {{name: '{schema.name}'}}) "
            f"SET s += {schema_props}"
        )
        
        # Create entity nodes
        for entity in schema.entities.values():
            entity_label = f"{label_prefix}Entity"
            props = {
                "name": entity.name,
                "is_abstract": entity.is_abstract,
                "attribute_count": len(entity.attributes),
                "schema": schema.name,
            }
            props_str = json.dumps(props)
            statements.append(
                f"MERGE (e:{entity_label} {{name: '{entity.name}', schema: '{schema.name}'}}) "
                f"SET e += {props_str}"
            )
        
        # Create type nodes
        for express_type in schema.types.values():
            type_label = f"{label_prefix}Type"
            props = {
                "name": express_type.name,
                "kind": express_type.kind,
                "schema": schema.name,
            }
            if express_type.options:
                props["options"] = express_type.options
            props_str = json.dumps(props)
            statements.append(
                f"MERGE (t:{type_label} {{name: '{express_type.name}', schema: '{schema.name}'}}) "
                f"SET t += {props_str}"
            )
        
        if include_relationships:
            # Entity belongs to Schema
            for entity in schema.entities.values():
                statements.append(
                    f"MATCH (e:{label_prefix}Entity {{name: '{entity.name}', schema: '{schema.name}'}}), "
                    f"(s:{label_prefix}Schema {{name: '{schema.name}'}}) "
                    f"MERGE (e)-[:BELONGS_TO]->(s)"
                )
            
            # Inheritance relationships
            for entity in schema.entities.values():
                if entity.supertype:
                    statements.append(
                        f"MATCH (child:{label_prefix}Entity {{name: '{entity.name}', schema: '{schema.name}'}}), "
                        f"(parent:{label_prefix}Entity {{name: '{entity.supertype}'}}) "
                        f"MERGE (child)-[:SUBTYPE_OF]->(parent)"
                    )
            
            # Attribute relationships to types
            for entity in schema.entities.values():
                for attr in entity.attributes:
                    # Try to match type reference to an entity or type
                    clean_type = attr.type_ref.split()[0] if attr.type_ref else ""
                    if clean_type and clean_type.upper() not in ['STRING', 'INTEGER', 'REAL', 'BOOLEAN', 'BINARY', 'NUMBER', 'LOGICAL']:
                        statements.append(
                            f"MATCH (e:{label_prefix}Entity {{name: '{entity.name}', schema: '{schema.name}'}}) "
                            f"OPTIONAL MATCH (t {{name: '{clean_type}'}}) "
                            f"FOREACH (x IN CASE WHEN t IS NOT NULL THEN [1] ELSE [] END | "
                            f"MERGE (e)-[:HAS_ATTRIBUTE {{name: '{attr.name}', optional: {str(attr.optional).lower()}}}]->(t))"
                        )
        
        return statements
    
    @staticmethod
    def schema_to_nodes_and_edges(
        schema: ExpressSchema
    ) -> Dict[str, Any]:
        """
        Convert schema to generic nodes and edges format.
        
        Returns:
            Dictionary with 'nodes' and 'edges' lists
        """
        nodes = []
        edges = []
        
        # Schema node
        nodes.append({
            "id": f"schema:{schema.name}",
            "type": "Schema",
            "properties": {
                "name": schema.name,
                "source_file": schema.source_file,
            }
        })
        
        # Entity nodes
        for entity in schema.entities.values():
            nodes.append({
                "id": f"entity:{schema.name}:{entity.name}",
                "type": "Entity",
                "properties": {
                    "name": entity.name,
                    "is_abstract": entity.is_abstract,
                    "schema": schema.name,
                    "attributes": [a.name for a in entity.attributes],
                }
            })
            
            # Entity -> Schema edge
            edges.append({
                "source": f"entity:{schema.name}:{entity.name}",
                "target": f"schema:{schema.name}",
                "type": "BELONGS_TO"
            })
            
            # Inheritance edge
            if entity.supertype:
                edges.append({
                    "source": f"entity:{schema.name}:{entity.name}",
                    "target": f"entity:{schema.name}:{entity.supertype}",
                    "type": "SUBTYPE_OF"
                })
        
        # Type nodes
        for express_type in schema.types.values():
            nodes.append({
                "id": f"type:{schema.name}:{express_type.name}",
                "type": "ExpressType",
                "properties": {
                    "name": express_type.name,
                    "kind": express_type.kind,
                    "schema": schema.name,
                    "options": express_type.options,
                }
            })
        
        return {"nodes": nodes, "edges": edges}


class ExpressExporter:
    """
    Export EXPRESS schemas to various formats.
    """
    
    @staticmethod
    def to_json(schema: ExpressSchema, pretty: bool = True) -> str:
        """Export schema to JSON"""
        data = schema.model_dump()
        # Convert datetime to string
        if data.get('parsed_at'):
            data['parsed_at'] = data['parsed_at'].isoformat()
        return json.dumps(data, indent=2 if pretty else None)
    
    @staticmethod
    def to_json_file(schema: ExpressSchema, file_path: str) -> None:
        """Export schema to JSON file"""
        json_content = ExpressExporter.to_json(schema)
        Path(file_path).write_text(json_content, encoding='utf-8')
    
    @staticmethod
    def to_markdown(schema: ExpressSchema) -> str:
        """Export schema documentation to Markdown"""
        lines = [
            f"# {schema.name}",
            "",
            f"**Source:** `{schema.source_file}`",
            f"**Parsed:** {schema.parsed_at.isoformat() if schema.parsed_at else 'N/A'}",
            "",
            "## Statistics",
            "",
            f"- **Entities:** {len(schema.entities)}",
            f"- **Types:** {len(schema.types)}",
            f"- **Imports:** {len(schema.imports)}",
            f"- **Functions:** {len(schema.functions)}",
            f"- **Rules:** {len(schema.rules)}",
            "",
        ]
        
        if schema.imports:
            lines.extend([
                "## Imports",
                "",
            ])
            for imp in schema.imports:
                comment = f" ({imp.comment})" if imp.comment else ""
                lines.append(f"- `{imp.schema_name}`{comment}")
            lines.append("")
        
        if schema.entities:
            lines.extend([
                "## Entities",
                "",
            ])
            for entity in sorted(schema.entities.values(), key=lambda e: e.name):
                abstract_marker = " *(abstract)*" if entity.is_abstract else ""
                supertype_info = f" → {entity.supertype}" if entity.supertype else ""
                lines.append(f"### {entity.name}{abstract_marker}{supertype_info}")
                lines.append("")
                
                if entity.attributes:
                    lines.append("| Attribute | Type | Optional |")
                    lines.append("|-----------|------|----------|")
                    for attr in entity.attributes:
                        opt = "✓" if attr.optional else ""
                        lines.append(f"| `{attr.name}` | `{attr.type_ref}` | {opt} |")
                    lines.append("")
        
        if schema.types:
            lines.extend([
                "## Types",
                "",
            ])
            for t in sorted(schema.types.values(), key=lambda t: t.name):
                lines.append(f"### {t.name}")
                lines.append(f"**Kind:** {t.kind}")
                if t.base_type:
                    lines.append(f"**Base:** `{t.base_type}`")
                if t.options:
                    lines.append(f"**Options:** {', '.join(t.options)}")
                lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def to_graphml(schema: ExpressSchema) -> str:
        """Export schema to GraphML format for visualization"""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            '  <key id="name" for="node" attr.name="name" attr.type="string"/>',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="relationship" for="edge" attr.name="relationship" attr.type="string"/>',
            f'  <graph id="{schema.name}" edgedefault="directed">',
        ]
        
        # Add entity nodes
        for entity in schema.entities.values():
            lines.extend([
                f'    <node id="{entity.name}">',
                f'      <data key="name">{entity.name}</data>',
                f'      <data key="type">Entity</data>',
                '    </node>',
            ])
        
        # Add inheritance edges
        edge_id = 0
        for entity in schema.entities.values():
            if entity.supertype:
                lines.extend([
                    f'    <edge id="e{edge_id}" source="{entity.name}" target="{entity.supertype}">',
                    '      <data key="relationship">SUBTYPE_OF</data>',
                    '    </edge>',
                ])
                edge_id += 1
        
        lines.extend([
            '  </graph>',
            '</graphml>',
        ])
        
        return "\n".join(lines)


def get_express_file_info(file_path: str) -> Dict[str, Any]:
    """
    Get basic info about an EXPRESS file without full parsing.
    
    Args:
        file_path: Path to EXPRESS file
        
    Returns:
        Dictionary with basic file info
    """
    path = Path(file_path)
    
    if not path.exists():
        return {"error": f"File not found: {file_path}"}
    
    content = path.read_text(encoding='utf-8', errors='replace')
    
    # Extract schema name
    import re
    schema_match = re.search(r'SCHEMA\s+(\w+)\s*;', content, re.IGNORECASE)
    schema_name = schema_match.group(1) if schema_match else "unknown"
    
    # Count constructs
    entity_count = len(re.findall(r'\bENTITY\s+\w+', content, re.IGNORECASE))
    type_count = len(re.findall(r'\bTYPE\s+\w+\s*=', content, re.IGNORECASE))
    use_count = len(re.findall(r'\bUSE\s+FROM\s+\w+', content, re.IGNORECASE))
    
    return {
        "file_path": str(path),
        "file_name": path.name,
        "file_size": path.stat().st_size,
        "schema_name": schema_name,
        "estimated_entities": entity_count,
        "estimated_types": type_count,
        "estimated_imports": use_count,
        "line_count": content.count('\n') + 1,
    }
