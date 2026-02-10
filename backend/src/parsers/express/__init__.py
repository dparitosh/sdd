"""
EXPRESS Parser Package
============================================================================
Modular EXPRESS language parser for ISO 10303-11 schemas.
Supports SMRL ARM/MIM modules and STEP specifications.

This package provides:
- ExpressParser: Core parsing engine
- Data models: ExpressSchema, ExpressEntity, ExpressType, etc.
- Utilities: Analysis, Neo4j conversion, export functions

Usage:
    from backend.src.parsers.express import ExpressParser, parse_express_file
    
    # Using the parser class
    parser = ExpressParser()
    result = parser.parse_file("path/to/schema.exp")
    
    # Using convenience function
    result = parse_express_file("path/to/schema.exp")
    
    # With analysis utilities
    from backend.src.parsers.express import ExpressAnalyzer
    stats = ExpressAnalyzer.get_schema_statistics(result.parsed_schema)
"""

from .models import (
    ExpressAttribute,
    ExpressEntity,
    ExpressType,
    ExpressFunction,
    ExpressRule,
    ExpressImport,
    ExpressSchema,
    ParseResult,
    DirectoryParseResult,
)

from .parser import (
    ExpressParser,
    parse_express_file,
    parse_express_directory,
)

from .utils import (
    ExpressAnalyzer,
    ExpressNeo4jConverter,
    ExpressExporter,
    get_express_file_info,
)

__all__ = [
    # Models
    "ExpressAttribute",
    "ExpressEntity", 
    "ExpressType",
    "ExpressFunction",
    "ExpressRule",
    "ExpressImport",
    "ExpressSchema",
    "ParseResult",
    "DirectoryParseResult",
    # Parser
    "ExpressParser",
    "parse_express_file",
    "parse_express_directory",
    # Utilities
    "ExpressAnalyzer",
    "ExpressNeo4jConverter", 
    "ExpressExporter",
    "get_express_file_info",
]

__version__ = "1.0.0"

__version__ = "1.0.0"
