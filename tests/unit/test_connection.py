"""Unit tests for Neo4j connection"""

import os

from unittest.mock import Mock, patch

import pytest

from src.graph.connection import Neo4jConnection


def test_connection_initialization():
    """Test Neo4j connection initialization"""
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")

    if not uri or not user or not password:
        pytest.skip("Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in .env or environment to run this test")

    conn = Neo4jConnection(uri, user, password)
    assert conn.uri == uri
    assert conn.user == user
    assert conn.password == password


def test_determine_label_from_connection():
    """Test connection context manager"""
    with patch("src.graph.connection.GraphDatabase") as mock_db:
        mock_driver = Mock()
        mock_db.driver.return_value = mock_driver

        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")

        if not uri or not user or not password:
            pytest.skip("Set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in .env or environment to run this test")

        with Neo4jConnection(uri, user, password) as conn:
            assert conn._driver is not None

        mock_driver.close.assert_called_once()
