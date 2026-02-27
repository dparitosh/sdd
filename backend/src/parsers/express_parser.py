"""
EXPRESS Schema Parser
============================================================================
Parses ISO 10303 EXPRESS (.exp) files to extract schema structure:
- SCHEMA declarations
- USE FROM imports
- ENTITY definitions with attributes
- TYPE definitions (SELECT, ENUMERATION, etc.)
- FUNCTION/PROCEDURE declarations
- RULE definitions

This parser provides the foundation for ingesting AP239, AP242, AP243 schemas
into the Neo4j knowledge graph.
"""

import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from loguru import logger


@dataclass
class ExpressAttribute:
    """Represents an attribute within an ENTITY"""
    name: str
    type_ref: str
    optional: bool = False
    is_list: bool = False
    inverse: bool = False
    derived: bool = False
    comment: Optional[str] = None


@dataclass
class ExpressEntity:
    """Represents an ENTITY definition"""
    name: str
    supertype: Optional[str] = None
    subtypes: List[str] = field(default_factory=list)
    attributes: List[ExpressAttribute] = field(default_factory=list)
    is_abstract: bool = False
    comment: Optional[str] = None


@dataclass
class ExpressType:
    """Represents a TYPE definition (SELECT, ENUMERATION, etc.)"""
    name: str
    kind: str  # 'SELECT', 'ENUMERATION', 'ALIAS', 'AGGREGATE'
    base_type: Optional[str] = None
    options: List[str] = field(default_factory=list)  # For SELECT or ENUM values
    comment: Optional[str] = None


@dataclass
class ExpressFunction:
    """Represents a FUNCTION or PROCEDURE"""
    name: str
    kind: str  # 'FUNCTION' or 'PROCEDURE'
    return_type: Optional[str] = None
    parameters: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class ExpressRule:
    """Represents a RULE definition"""
    name: str
    applies_to: List[str] = field(default_factory=list)


@dataclass 
class ExpressSchema:
    """Represents a complete EXPRESS SCHEMA"""
    name: str
    source_file: str
    uses: List[Tuple[str, Optional[str]]] = field(default_factory=list)  # (schema, comment)
    entities: Dict[str, ExpressEntity] = field(default_factory=dict)
    types: Dict[str, ExpressType] = field(default_factory=dict)
    functions: Dict[str, ExpressFunction] = field(default_factory=dict)
    rules: Dict[str, ExpressRule] = field(default_factory=dict)
    constants: Dict[str, str] = field(default_factory=dict)


class ExpressParser:
    """
    Parser for ISO 10303 EXPRESS schema files (.exp)
    
    Extracts structural information without executing the schema.
    Designed to work with AP239, AP242, AP243 schema modules.
    """
    
    def __init__(self):
        self.schemas: Dict[str, ExpressSchema] = {}
        
    def parse_file(self, filepath: Path) -> Optional[ExpressSchema]:
        """Parse a single EXPRESS file and return the schema"""
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return None
            
        logger.info(f"Parsing EXPRESS file: {filepath.name}")
        
        try:
            content = filepath.read_text(encoding='utf-8', errors='replace')
            return self._parse_content(content, str(filepath))
        except Exception as e:
            logger.error(f"Error parsing {filepath}: {e}")
            return None
    
    def _parse_content(self, content: str, source_file: str) -> Optional[ExpressSchema]:
        """Parse EXPRESS content string"""
        # Remove comments (multi-line)
        content_no_comments = self._strip_comments(content)
        
        # Extract schema name
        schema_match = re.search(r'SCHEMA\s+(\w+)\s*;', content_no_comments, re.IGNORECASE)
        if not schema_match:
            logger.warning(f"No SCHEMA found in {source_file}")
            return None
            
        schema_name = schema_match.group(1)
        schema = ExpressSchema(name=schema_name, source_file=source_file)
        
        # Parse USE FROM statements
        schema.uses = self._parse_use_from(content)
        
        # Parse ENTITY definitions
        schema.entities = self._parse_entities(content_no_comments)
        
        # Parse TYPE definitions
        schema.types = self._parse_types(content_no_comments)
        
        # Parse FUNCTION/PROCEDURE definitions
        schema.functions = self._parse_functions(content_no_comments)
        
        # Parse RULE definitions
        schema.rules = self._parse_rules(content_no_comments)
        
        # Parse CONSTANT definitions
        schema.constants = self._parse_constants(content_no_comments)
        
        self.schemas[schema_name] = schema
        
        logger.info(f"  Schema: {schema_name}")
        logger.info(f"  - Imports: {len(schema.uses)}")
        logger.info(f"  - Entities: {len(schema.entities)}")
        logger.info(f"  - Types: {len(schema.types)}")
        logger.info(f"  - Functions: {len(schema.functions)}")
        
        return schema
    
    def _strip_comments(self, content: str) -> str:
        """Remove EXPRESS comments (* ... *)"""
        # Multi-line comments
        content = re.sub(r'\(\*.*?\*\)', '', content, flags=re.DOTALL)
        # Single-line comments (-- style, if any)
        content = re.sub(r'--.*$', '', content, flags=re.MULTILINE)
        return content
    
    def _parse_use_from(self, content: str) -> List[Tuple[str, Optional[str]]]:
        """Parse USE FROM statements with their comments"""
        uses = []
        # Pattern: USE FROM Schema_name; -- ISO/TS comment
        pattern = r'USE\s+FROM\s+(\w+)(?:_arm)?(?:_mim)?;?\s*(?:--\s*(.*))?'
        for match in re.finditer(pattern, content, re.IGNORECASE):
            schema_name = match.group(1)
            comment = match.group(2).strip() if match.group(2) else None
            uses.append((schema_name, comment))
        return uses
    
    def _parse_entities(self, content: str) -> Dict[str, ExpressEntity]:
        """Parse ENTITY definitions"""
        entities = {}
        
        # Pattern to find ENTITY blocks
        entity_pattern = r'ENTITY\s+(\w+)(?:\s+ABSTRACT)?\s*(?:SUBTYPE\s+OF\s*\(([^)]+)\))?\s*;(.*?)END_ENTITY\s*;'
        
        for match in re.finditer(entity_pattern, content, re.IGNORECASE | re.DOTALL):
            name = match.group(1)
            supertype_str = match.group(2)
            body = match.group(3)
            
            entity = ExpressEntity(name=name)
            
            # Check if abstract
            if 'ABSTRACT' in match.group(0).upper().split('ENTITY')[0] or \
               'ABSTRACT' in match.group(0).upper().split(name)[0]:
                entity.is_abstract = True
            
            # Parse supertypes
            if supertype_str:
                supertypes = [s.strip() for s in supertype_str.split(',')]
                entity.supertype = supertypes[0] if supertypes else None
            
            # Parse attributes from body
            entity.attributes = self._parse_entity_attributes(body)
            
            entities[name] = entity
            
        return entities
    
    def _parse_entity_attributes(self, body: str) -> List[ExpressAttribute]:
        """Parse attributes within an ENTITY body"""
        attributes = []
        
        # Split into sections
        sections = re.split(r'\b(DERIVE|INVERSE|UNIQUE|WHERE)\b', body, flags=re.IGNORECASE)
        
        # Main attributes section (before DERIVE/INVERSE/etc.)
        main_section = sections[0] if sections else body
        
        # Pattern: attr_name : OPTIONAL? type_ref;
        attr_pattern = r'(\w+)\s*:\s*(OPTIONAL\s+)?(LIST|SET|BAG|ARRAY)?\s*(?:\[[\d:?]+\]\s*OF\s+)?(\w+(?:\s*\([^)]*\))?)\s*;'
        
        for match in re.finditer(attr_pattern, main_section, re.IGNORECASE):
            attr = ExpressAttribute(
                name=match.group(1),
                type_ref=match.group(4).strip(),
                optional=bool(match.group(2)),
                is_list=bool(match.group(3))
            )
            attributes.append(attr)
        
        # Parse INVERSE attributes
        for i, section in enumerate(sections):
            if section.upper() == 'INVERSE' and i + 1 < len(sections):
                inv_section = sections[i + 1]
                for match in re.finditer(attr_pattern, inv_section, re.IGNORECASE):
                    attr = ExpressAttribute(
                        name=match.group(1),
                        type_ref=match.group(4).strip(),
                        inverse=True
                    )
                    attributes.append(attr)
            elif section.upper() == 'DERIVE' and i + 1 < len(sections):
                deriv_section = sections[i + 1]
                # Simplified derived attribute parsing
                deriv_pattern = r'(\w+)\s*:\s*(\w+)'
                for match in re.finditer(deriv_pattern, deriv_section, re.IGNORECASE):
                    attr = ExpressAttribute(
                        name=match.group(1),
                        type_ref=match.group(2),
                        derived=True
                    )
                    attributes.append(attr)
        
        return attributes
    
    def _parse_types(self, content: str) -> Dict[str, ExpressType]:
        """Parse TYPE definitions"""
        types = {}
        
        # SELECT type pattern
        select_pattern = r'TYPE\s+(\w+)\s*=\s*SELECT\s*(?:BASED_ON\s+\w+\s+WITH)?\s*\(([^)]+)\)\s*;'
        for match in re.finditer(select_pattern, content, re.IGNORECASE | re.DOTALL):
            name = match.group(1)
            options_str = match.group(2)
            options = [o.strip() for o in options_str.split(',') if o.strip()]
            types[name] = ExpressType(name=name, kind='SELECT', options=options)
        
        # ENUMERATION type pattern
        enum_pattern = r'TYPE\s+(\w+)\s*=\s*ENUMERATION\s+OF\s*\(([^)]+)\)\s*;'
        for match in re.finditer(enum_pattern, content, re.IGNORECASE | re.DOTALL):
            name = match.group(1)
            options_str = match.group(2)
            options = [o.strip() for o in options_str.split(',') if o.strip()]
            types[name] = ExpressType(name=name, kind='ENUMERATION', options=options)
        
        # Simple ALIAS type pattern (TYPE x = y;)
        alias_pattern = r'TYPE\s+(\w+)\s*=\s*(\w+)\s*;'
        for match in re.finditer(alias_pattern, content, re.IGNORECASE):
            name = match.group(1)
            base = match.group(2)
            if name not in types:  # Don't overwrite SELECT/ENUM
                types[name] = ExpressType(name=name, kind='ALIAS', base_type=base)
        
        return types
    
    def _parse_functions(self, content: str) -> Dict[str, ExpressFunction]:
        """Parse FUNCTION and PROCEDURE definitions"""
        functions = {}
        
        # FUNCTION pattern
        func_pattern = r'FUNCTION\s+(\w+)\s*(?:\([^)]*\))?\s*:\s*(\w+)'
        for match in re.finditer(func_pattern, content, re.IGNORECASE):
            name = match.group(1)
            return_type = match.group(2)
            functions[name] = ExpressFunction(name=name, kind='FUNCTION', return_type=return_type)
        
        # PROCEDURE pattern
        proc_pattern = r'PROCEDURE\s+(\w+)'
        for match in re.finditer(proc_pattern, content, re.IGNORECASE):
            name = match.group(1)
            if name not in functions:
                functions[name] = ExpressFunction(name=name, kind='PROCEDURE')
        
        return functions
    
    def _parse_rules(self, content: str) -> Dict[str, ExpressRule]:
        """Parse RULE definitions"""
        rules = {}
        
        rule_pattern = r'RULE\s+(\w+)\s+FOR\s*\(([^)]+)\)'
        for match in re.finditer(rule_pattern, content, re.IGNORECASE):
            name = match.group(1)
            applies_to = [a.strip() for a in match.group(2).split(',')]
            rules[name] = ExpressRule(name=name, applies_to=applies_to)
        
        return rules
    
    def _parse_constants(self, content: str) -> Dict[str, str]:
        """Parse CONSTANT definitions"""
        constants = {}
        
        # Find CONSTANT block
        const_block = re.search(r'CONSTANT(.*?)END_CONSTANT', content, re.IGNORECASE | re.DOTALL)
        if const_block:
            block = const_block.group(1)
            const_pattern = r'(\w+)\s*:\s*[^=]+=\s*([^;]+);'
            for match in re.finditer(const_pattern, block):
                constants[match.group(1)] = match.group(2).strip()
        
        return constants


def parse_express_directory(directory: Path, pattern: str = "*.exp") -> Dict[str, ExpressSchema]:
    """
    Parse all EXPRESS files in a directory.
    
    Args:
        directory: Path to directory containing .exp files
        pattern: Glob pattern for finding files (default: *.exp)
    
    Returns:
        Dictionary mapping schema names to ExpressSchema objects
    """
    parser = ExpressParser()
    
    if not directory.exists():
        logger.error(f"Directory not found: {directory}")
        return {}
    
    exp_files = list(directory.glob(pattern))
    logger.info(f"Found {len(exp_files)} EXPRESS files in {directory}")
    
    for exp_file in exp_files:
        parser.parse_file(exp_file)
    
    return parser.schemas
