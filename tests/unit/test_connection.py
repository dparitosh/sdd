"""Unit tests for Neo4j connection"""

from unittest.mock import Mock, patch

import pytest

from src.graph.connection import Neo4jConnection


def test_connection_initialization():
    """Test Neo4j connection initialization"""
    conn = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
    assert conn.uri == "bolt://localhost:7687"
    assert conn.user == "neo4j"
    assert conn.password == "password"


def test_determine_label_from_connection():
    """Test connection context manager"""
    with patch("src.graph.connection.GraphDatabase") as mock_db:
        mock_driver = Mock()
        mock_db.driver.return_value = mock_driver

        with Neo4jConnection("bolt://localhost:7687", "neo4j", "password") as conn:
            assert conn._driver is not None

        mock_driver.close.assert_called_once()
