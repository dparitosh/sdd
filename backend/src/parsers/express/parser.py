"""
EXPRESS Parser Core Engine
============================================================================
Core parsing logic for ISO 10303-11 EXPRESS schemas.
Supports ARM and MIM modules from SMRL and STEP specifications.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .models import (
    ExpressAttribute,
    ExpressEntity,
    ExpressFunction,
    ExpressImport,
    ExpressRule,
    ExpressSchema,
    ExpressType,
    ParseResult,
    DirectoryParseResult,
)


class ExpressParser:
    """
    Parser for ISO 10303-11 EXPRESS language schemas.
    
    Features:
    - Parse SCHEMA, ENTITY, TYPE, FUNCTION, RULE definitions
    - Extract USE FROM imports with ISO comments
    - Handle inheritance and SELECT types
    - Extract attributes with cardinality and optionality
    
    Usage:
        parser = ExpressParser()
        result = parser.parse_file("path/to/schema.exp")
        if result.success:
            schema = result.parsed_schema
            for entity in schema.entities.values():
                print(f"Entity: {entity.name}")
    """
    
    # Regex patterns for EXPRESS constructs
    PATTERNS = {
        'schema': re.compile(r'SCHEMA\s+(\w+)\s*;', re.IGNORECASE),
        'end_schema': re.compile(r'END_SCHEMA\s*;', re.IGNORECASE),
        'use_from': re.compile(
            r'USE\s+FROM\s+(\w+)',
            re.IGNORECASE
        ),
        'use_from_with_comment': re.compile(
            r'USE\s+FROM\s+(\w+)[^;]*;\s*--\s*(ISO[^\n]*)',
            re.IGNORECASE | re.DOTALL
        ),
        'entity_start': re.compile(
            r'ENTITY\s+(\w+)\s*(ABSTRACT)?\s*(SUPERTYPE\s+OF[^;]*)?(?:SUBTYPE\s+OF\s*\(([^)]+)\))?\s*;',
            re.IGNORECASE
        ),
        'entity_simple': re.compile(r'ENTITY\s+(\w+)', re.IGNORECASE),
        'end_entity': re.compile(r'END_ENTITY\s*;', re.IGNORECASE),
        'type_start': re.compile(r'TYPE\s+(\w+)\s*=\s*', re.IGNORECASE),
        'end_type': re.compile(r'END_TYPE\s*;', re.IGNORECASE),
        'function_start': re.compile(r'FUNCTION\s+(\w+)', re.IGNORECASE),
        'procedure_start': re.compile(r'PROCEDURE\s+(\w+)', re.IGNORECASE),
        'end_function': re.compile(r'END_FUNCTION\s*;', re.IGNORECASE),
        'end_procedure': re.compile(r'END_PROCEDURE\s*;', re.IGNORECASE),
        'rule_start': re.compile(r'RULE\s+(\w+)\s+FOR\s*\(([^)]+)\)', re.IGNORECASE),
        'end_rule': re.compile(r'END_RULE\s*;', re.IGNORECASE),
        'constant': re.compile(r'CONSTANT\s+(\w+)\s*:', re.IGNORECASE),
        'select_type': re.compile(r'SELECT\s*\(([^)]+)\)', re.IGNORECASE | re.DOTALL),
        'enum_type': re.compile(r'ENUMERATION\s+OF\s*\(([^)]+)\)', re.IGNORECASE | re.DOTALL),
        'attribute': re.compile(
            r'^\s*(\w+)\s*:\s*(OPTIONAL\s+)?(SET|LIST|BAG|ARRAY)?\s*(\[[\d:?]+\])?\s*(OF)?\s*(.+?)\s*;',
            re.IGNORECASE | re.MULTILINE
        ),
        'inverse_attr': re.compile(
            r'^\s*(\w+)\s*:\s*(SET|BAG)?\s*(\[[\d:?]+\])?\s*(OF)?\s*(\w+)\s+FOR\s+\w+\s*;',
            re.IGNORECASE | re.MULTILINE
        ),
        'derive_section': re.compile(r'DERIVE', re.IGNORECASE),
        'inverse_section': re.compile(r'INVERSE', re.IGNORECASE),
        'unique_section': re.compile(r'UNIQUE', re.IGNORECASE),
        'where_section': re.compile(r'WHERE', re.IGNORECASE),
    }
    
    def __init__(self, strict_mode: bool = False):
        """
        Initialize the EXPRESS parser.
        
        Args:
            strict_mode: If True, raise errors on parse issues; otherwise collect warnings
        """
        self.strict_mode = strict_mode
        self._warnings: List[str] = []
    
    def parse_file(self, file_path: str) -> ParseResult:
        """
        Parse an EXPRESS schema file.
        
        Args:
            file_path: Path to the .exp file
            
        Returns:
            ParseResult containing the parsed schema or error information
        """
        start_time = time.time()
        self._warnings = []
        
        try:
            path = Path(file_path)
            if not path.exists():
                return ParseResult(
                    success=False,
                    error=f"File not found: {file_path}",
                    parse_time_ms=(time.time() - start_time) * 1000
                )
            
            if path.suffix.lower() != '.exp':
                self._warnings.append(f"File does not have .exp extension: {file_path}")
            
            content = path.read_text(encoding='utf-8', errors='replace')
            schema = self._parse_content(content, str(path))
            
            return ParseResult(
                success=True,
                parsed_schema=schema,
                warnings=self._warnings.copy(),
                parse_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e),
                warnings=self._warnings.copy(),
                parse_time_ms=(time.time() - start_time) * 1000
            )
    
    def parse_string(self, content: str, source_name: str = "string") -> ParseResult:
        """
        Parse EXPRESS content from a string.
        
        Args:
            content: EXPRESS schema content
            source_name: Name to use for the source in the result
            
        Returns:
            ParseResult containing the parsed schema
        """
        start_time = time.time()
        self._warnings = []
        
        try:
            schema = self._parse_content(content, source_name)
            return ParseResult(
                success=True,
                parsed_schema=schema,
                warnings=self._warnings.copy(),
                parse_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ParseResult(
                success=False,
                error=str(e),
                warnings=self._warnings.copy(),
                parse_time_ms=(time.time() - start_time) * 1000
            )
    
    def parse_directory(
        self,
        directory: str,
        recursive: bool = True,
        pattern: str = "*.exp"
    ) -> DirectoryParseResult:
        """
        Parse all EXPRESS files in a directory.
        
        Args:
            directory: Directory path to search
            recursive: Whether to search subdirectories
            pattern: Glob pattern for EXPRESS files
            
        Returns:
            DirectoryParseResult with all parsed schemas
        """
        start_time = time.time()
        path = Path(directory)
        
        if not path.exists():
            return DirectoryParseResult(
                directory=directory,
                errors=[{"file": directory, "error": "Directory not found"}],
                parse_time_ms=(time.time() - start_time) * 1000
            )
        
        # Find all EXPRESS files
        if recursive:
            files = list(path.rglob(pattern))
        else:
            files = list(path.glob(pattern))
        
        schemas = {}
        errors = []
        
        for file_path in files:
            result = self.parse_file(str(file_path))
            if result.success and result.parsed_schema:
                schemas[result.parsed_schema.name] = result.parsed_schema
            else:
                errors.append({
                    "file": str(file_path),
                    "error": result.error or "Unknown error"
                })
        
        return DirectoryParseResult(
            directory=directory,
            total_files=len(files),
            successful=len(schemas),
            failed=len(errors),
            schemas=schemas,
            errors=errors,
            parse_time_ms=(time.time() - start_time) * 1000
        )
    
    def _parse_content(self, content: str, source_file: str) -> ExpressSchema:
        """Parse EXPRESS content and return schema object"""
        
        # Extract schema name
        schema_match = self.PATTERNS['schema'].search(content)
        schema_name = schema_match.group(1) if schema_match else "unknown"
        
        # Create schema object
        schema = ExpressSchema(
            name=schema_name,
            source_file=source_file,
            parsed_at=datetime.now()
        )
        
        # Parse imports
        schema.imports = self._parse_imports(content)
        
        # Parse types
        schema.types = self._parse_types(content)
        
        # Parse entities
        schema.entities = self._parse_entities(content)
        
        # Parse functions and procedures
        schema.functions = self._parse_functions(content)
        
        # Parse rules
        schema.rules = self._parse_rules(content)
        
        return schema
    
    def _parse_imports(self, content: str) -> List[ExpressImport]:
        """Extract USE FROM imports with ISO comments"""
        imports = []
        
        # Try to get imports with ISO comments first
        for match in self.PATTERNS['use_from_with_comment'].finditer(content):
            imports.append(ExpressImport(
                schema_name=match.group(1),
                comment=match.group(2).strip() if match.group(2) else None
            ))
        
        # Get simple USE FROM without grabbing duplicates
        found_schemas = {imp.schema_name for imp in imports}
        for match in self.PATTERNS['use_from'].finditer(content):
            schema_name = match.group(1)
            if schema_name not in found_schemas:
                imports.append(ExpressImport(schema_name=schema_name))
                found_schemas.add(schema_name)
        
        return imports
    
    def _parse_types(self, content: str) -> dict:
        """Extract TYPE definitions"""
        types = {}
        
        # Find TYPE ... END_TYPE blocks
        type_pattern = re.compile(
            r'TYPE\s+(\w+)\s*=\s*([^;]+;.*?)END_TYPE\s*;',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in type_pattern.finditer(content):
            type_name = match.group(1)
            type_body = match.group(2)
            
            express_type = self._parse_type_definition(type_name, type_body)
            if express_type:
                types[type_name] = express_type
        
        return types
    
    def _parse_type_definition(self, name: str, body: str) -> Optional[ExpressType]:
        """Parse a single TYPE definition body"""
        
        # Check for SELECT type
        select_match = self.PATTERNS['select_type'].search(body)
        if select_match:
            options = [opt.strip() for opt in select_match.group(1).split(',')]
            return ExpressType(name=name, kind="SELECT", options=options)
        
        # Check for ENUMERATION type
        enum_match = self.PATTERNS['enum_type'].search(body)
        if enum_match:
            options = [opt.strip() for opt in enum_match.group(1).split(',')]
            return ExpressType(name=name, kind="ENUMERATION", options=options)
        
        # Check for aggregate types (SET, LIST, BAG, ARRAY)
        aggregate_match = re.search(r'(SET|LIST|BAG|ARRAY)\s*(\[.*?\])?\s*OF\s+(\w+)', body, re.IGNORECASE)
        if aggregate_match:
            return ExpressType(
                name=name,
                kind="AGGREGATE",
                base_type=f"{aggregate_match.group(1)} OF {aggregate_match.group(3)}"
            )
        
        # Simple alias type
        simple_match = re.match(r'\s*(\w+)', body)
        if simple_match:
            return ExpressType(name=name, kind="ALIAS", base_type=simple_match.group(1))
        
        return ExpressType(name=name, kind="UNKNOWN")
    
    def _parse_entities(self, content: str) -> dict:
        """Extract ENTITY definitions"""
        entities = {}
        
        # Find ENTITY ... END_ENTITY blocks
        entity_pattern = re.compile(
            r'ENTITY\s+(\w+)\s*(ABSTRACT)?\s*(SUPERTYPE\s+OF\s*\([^)]+\))?\s*'
            r'(?:SUBTYPE\s+OF\s*\(([^)]+)\))?\s*;(.*?)END_ENTITY\s*;',
            re.IGNORECASE | re.DOTALL
        )
        
        for match in entity_pattern.finditer(content):
            entity_name = match.group(1)
            is_abstract = match.group(2) is not None
            supertype_of = match.group(3)
            subtype_of = match.group(4)
            entity_body = match.group(5)
            
            # Parse supertype reference
            supertype = None
            if subtype_of:
                supertypes = [s.strip() for s in subtype_of.split(',')]
                supertype = supertypes[0] if supertypes else None
            
            # Extract subtypes from SUPERTYPE OF clause
            subtypes = []
            if supertype_of:
                subtype_match = re.search(r'ONEOF\s*\(([^)]+)\)', supertype_of, re.IGNORECASE)
                if subtype_match:
                    subtypes = [s.strip() for s in subtype_match.group(1).split(',')]
            
            # Parse attributes
            attributes = self._parse_entity_attributes(entity_body)
            
            entities[entity_name] = ExpressEntity(
                name=entity_name,
                supertype=supertype,
                subtypes=subtypes,
                attributes=attributes,
                is_abstract=is_abstract
            )
        
        return entities
    
    def _parse_entity_attributes(self, body: str) -> List[ExpressAttribute]:
        """Parse attributes from entity body"""
        attributes = []
        
        # Split body into sections
        derive_pos = self._find_section(body, 'DERIVE')
        inverse_pos = self._find_section(body, 'INVERSE')
        unique_pos = self._find_section(body, 'UNIQUE')
        where_pos = self._find_section(body, 'WHERE')
        
        # Determine end of regular attributes section
        sections = [p for p in [derive_pos, inverse_pos, unique_pos, where_pos] if p > -1]
        attr_end = min(sections) if sections else len(body)
        
        # Parse regular attributes
        attr_section = body[:attr_end]
        for match in self.PATTERNS['attribute'].finditer(attr_section):
            attr_name = match.group(1).strip()
            is_optional = match.group(2) is not None
            collection_type = match.group(3)
            type_ref = match.group(6).strip() if match.group(6) else "UNKNOWN"
            
            # Clean up type reference
            type_ref = re.sub(r'\s+', ' ', type_ref)
            
            attributes.append(ExpressAttribute(
                name=attr_name,
                type_ref=type_ref,
                optional=is_optional,
                is_list=collection_type is not None,
                inverse=False,
                derived=False
            ))
        
        # Parse DERIVE section
        if derive_pos > -1:
            derive_end = min([p for p in sections if p > derive_pos], default=len(body))
            derive_section = body[derive_pos:derive_end]
            for match in re.finditer(r'(\w+)\s*:', derive_section):
                attr_name = match.group(1)
                if attr_name.upper() != 'DERIVE':
                    attributes.append(ExpressAttribute(
                        name=attr_name,
                        type_ref="DERIVED",
                        optional=True,
                        derived=True
                    ))
        
        # Parse INVERSE section
        if inverse_pos > -1:
            inverse_end = min([p for p in sections if p > inverse_pos], default=len(body))
            inverse_section = body[inverse_pos:inverse_end]
            for match in re.finditer(r'(\w+)\s*:\s*(SET|BAG)?\s*.*?\s+OF\s+(\w+)', inverse_section, re.IGNORECASE):
                attr_name = match.group(1)
                if attr_name.upper() != 'INVERSE':
                    attributes.append(ExpressAttribute(
                        name=attr_name,
                        type_ref=match.group(3) if match.group(3) else "UNKNOWN",
                        optional=True,
                        is_list=match.group(2) is not None,
                        inverse=True
                    ))
        
        return attributes
    
    def _find_section(self, body: str, section_name: str) -> int:
        """Find the position of a section keyword in entity body"""
        pattern = re.compile(rf'\b{section_name}\b', re.IGNORECASE)
        match = pattern.search(body)
        return match.start() if match else -1
    
    def _parse_functions(self, content: str) -> dict:
        """Extract FUNCTION and PROCEDURE definitions"""
        functions = {}
        
        # Parse FUNCTIONs
        func_pattern = re.compile(
            r'FUNCTION\s+(\w+)\s*\(([^)]*)\)\s*:\s*(\w+)',
            re.IGNORECASE
        )
        for match in func_pattern.finditer(content):
            name = match.group(1)
            params_str = match.group(2)
            return_type = match.group(3)
            
            params = self._parse_parameters(params_str)
            functions[name] = ExpressFunction(
                name=name,
                kind="FUNCTION",
                return_type=return_type,
                parameters=params
            )
        
        # Parse PROCEDUREs
        proc_pattern = re.compile(
            r'PROCEDURE\s+(\w+)\s*\(([^)]*)\)',
            re.IGNORECASE
        )
        for match in proc_pattern.finditer(content):
            name = match.group(1)
            params_str = match.group(2)
            
            params = self._parse_parameters(params_str)
            functions[name] = ExpressFunction(
                name=name,
                kind="PROCEDURE",
                parameters=params
            )
        
        return functions
    
    def _parse_parameters(self, params_str: str) -> List[dict]:
        """Parse function/procedure parameters"""
        params = []
        if not params_str.strip():
            return params
        
        for param in params_str.split(';'):
            param = param.strip()
            if not param:
                continue
            
            # Handle VAR prefix
            is_var = param.upper().startswith('VAR ')
            if is_var:
                param = param[4:].strip()
            
            # Parse name : type
            parts = param.split(':')
            if len(parts) >= 2:
                names = [n.strip() for n in parts[0].split(',')]
                type_ref = parts[1].strip()
                for name in names:
                    params.append({
                        "name": name,
                        "type": type_ref,
                        "is_var": is_var
                    })
        
        return params
    
    def _parse_rules(self, content: str) -> dict:
        """Extract RULE definitions"""
        rules = {}
        
        for match in self.PATTERNS['rule_start'].finditer(content):
            rule_name = match.group(1)
            applies_to = [e.strip() for e in match.group(2).split(',')]
            
            rules[rule_name] = ExpressRule(
                name=rule_name,
                applies_to=applies_to
            )
        
        return rules


# Convenience functions for quick usage
def parse_express_file(file_path: str) -> ParseResult:
    """Quick parse function for single file"""
    return ExpressParser().parse_file(file_path)


def parse_express_directory(directory: str, recursive: bool = True) -> DirectoryParseResult:
    """Quick parse function for directory"""
    return ExpressParser().parse_directory(directory, recursive)
