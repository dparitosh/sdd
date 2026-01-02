"""Unit tests for XMI parser"""

from pathlib import Path

import pytest

from src.parsers.xmi_parser import XMIParser


def test_xmi_parser_initialization():
    """Test XMI parser initialization"""
    parser = XMIParser()
    assert parser is not None
    assert "xmi" in parser.namespaces


def test_determine_label():
    """Test label determination from XMI type"""
    parser = XMIParser()

    assert parser._determine_label("uml:System") == "System"
    assert parser._determine_label("uml:Component") == "Component"
    assert parser._determine_label("uml:Requirement") == "Requirement"
    assert parser._determine_label("uml:Interface") == "Interface"
    assert parser._determine_label("uml:Property") == "Parameter"
    assert parser._determine_label("uml:Class") == "Element"


def test_determine_relationship_type():
    """Test relationship type determination"""
    parser = XMIParser()

    assert parser._determine_relationship_type("componentRef") == "HAS_COMPONENT"
    assert parser._determine_relationship_type("requirementRef") == "SATISFIES"
    assert parser._determine_relationship_type("interfaceRef") == "CONNECTS_TO"
    assert parser._determine_relationship_type("propertyRef") == "HAS_PARAMETER"
    assert parser._determine_relationship_type("otherRef") == "RELATES_TO"
