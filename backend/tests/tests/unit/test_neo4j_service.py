"""
Unit tests for Neo4jService
Tests database operations, connection pooling, and query execution
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from web.services.neo4j_service import Neo4jService, get_neo4j_service


class TestNeo4jService:
    """Test suite for Neo4jService class"""

    @pytest.fixture
    def mock_driver(self):
        """Create a mock Neo4j driver"""
        driver = MagicMock()
        driver.verify_connectivity = MagicMock()
        return driver

    @pytest.fixture
    def neo4j_service(self, mock_driver):
        """Create a Neo4jService instance with mocked driver"""
        with patch("web.services.neo4j_service.GraphDatabase.driver", return_value=mock_driver):
            service = Neo4jService(
                uri="neo4j+s://test.neo4j.io", user="test_user", password="test_password"
            )
            return service

    def test_singleton_pattern(self):
        """Test that get_neo4j_service returns the same instance"""
        with patch.dict(
            "os.environ",
            {
                "NEO4J_URI": "neo4j+s://test.neo4j.io",
                "NEO4J_USER": "test_user",
                "NEO4J_PASSWORD": "test_password",
            },
        ):
            with patch("web.services.neo4j_service.GraphDatabase.driver"):
                service1 = get_neo4j_service()
                service2 = get_neo4j_service()
                assert service1 is service2, "get_neo4j_service should return singleton"

    def test_initialization(self, neo4j_service, mock_driver):
        """Test service initialization"""
        assert neo4j_service.driver == mock_driver
        mock_driver.verify_connectivity.assert_called_once()

    def test_execute_query_success(self, neo4j_service, mock_driver):
        """Test successful query execution"""
        mock_session = MagicMock()
        mock_result = [{"name": "Class1", "id": "123"}, {"name": "Class2", "id": "456"}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        query = "MATCH (c:Class) RETURN c.name AS name, c.id AS id"
        result = neo4j_service.execute_query(query)

        assert result == mock_result
        mock_session.run.assert_called_once_with(query, None)

    def test_execute_query_with_parameters(self, neo4j_service, mock_driver):
        """Test query execution with parameters"""
        mock_session = MagicMock()
        mock_result = [{"name": "TestClass", "id": "789"}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        query = "MATCH (c:Class {id: $id}) RETURN c.name AS name, c.id AS id"
        params = {"id": "789"}
        result = neo4j_service.execute_query(query, params)

        assert result == mock_result
        mock_session.run.assert_called_once_with(query, params)

    def test_execute_query_error(self, neo4j_service, mock_driver):
        """Test query execution with database error"""
        mock_session = MagicMock()
        mock_session.run.side_effect = Exception("Database connection error")
        mock_driver.session.return_value.__enter__.return_value = mock_session

        query = "MATCH (c:Class) RETURN c"

        with pytest.raises(Exception) as exc_info:
            neo4j_service.execute_query(query)

        assert "Database connection error" in str(exc_info.value)

    def test_get_node_by_id(self, neo4j_service, mock_driver):
        """Test retrieving node by ID"""
        mock_session = MagicMock()
        mock_result = [{"node": {"id": "123", "name": "TestClass"}}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        node = neo4j_service.get_node_by_id("Class", "123")

        assert node == {"id": "123", "name": "TestClass"}
        mock_session.run.assert_called_once()

    def test_get_node_by_id_not_found(self, neo4j_service, mock_driver):
        """Test retrieving non-existent node"""
        mock_session = MagicMock()
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__.return_value = mock_session

        node = neo4j_service.get_node_by_id("Class", "nonexistent")

        assert node is None

    def test_get_node_by_uid(self, neo4j_service, mock_driver):
        """Test retrieving node by UID"""
        mock_session = MagicMock()
        mock_result = [{"node": {"uid": "uid-123", "name": "TestClass"}}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        node = neo4j_service.get_node_by_uid("Class", "uid-123")

        assert node == {"uid": "uid-123", "name": "TestClass"}

    def test_list_nodes(self, neo4j_service, mock_driver):
        """Test listing nodes with pagination"""
        mock_session = MagicMock()
        mock_result = [
            {"node": {"id": "1", "name": "Class1"}},
            {"node": {"id": "2", "name": "Class2"}},
        ]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        nodes = neo4j_service.list_nodes("Class", skip=0, limit=10)

        assert len(nodes) == 2
        assert nodes[0]["name"] == "Class1"
        assert nodes[1]["name"] == "Class2"

    def test_count_nodes(self, neo4j_service, mock_driver):
        """Test counting nodes by label"""
        mock_session = MagicMock()
        mock_result = [{"count": 42}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        count = neo4j_service.count_nodes("Class")

        assert count == 42

    def test_search_nodes(self, neo4j_service, mock_driver):
        """Test searching nodes by name"""
        mock_session = MagicMock()
        mock_result = [
            {"node": {"id": "1", "name": "PersonClass"}},
            {"node": {"id": "2", "name": "PersonManager"}},
        ]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        results = neo4j_service.search_nodes("Person", limit=10)

        assert len(results) == 2
        assert "Person" in results[0]["name"]

    def test_get_relationships(self, neo4j_service, mock_driver):
        """Test retrieving relationships for a node"""
        mock_session = MagicMock()
        mock_result = [
            {
                "rel_type": "GENERALIZES",
                "target_label": "Class",
                "target_node": {"id": "2", "name": "BaseClass"},
            }
        ]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        rels = neo4j_service.get_relationships("Class", "1")

        assert len(rels) == 1
        assert rels[0]["rel_type"] == "GENERALIZES"
        assert rels[0]["target_node"]["name"] == "BaseClass"

    def test_get_statistics(self, neo4j_service, mock_driver):
        """Test retrieving database statistics"""
        mock_session = MagicMock()

        # Mock total nodes count
        mock_session.run.return_value = [{"count": 3257}]
        mock_driver.session.return_value.__enter__.return_value = mock_session

        # Mock node types - need to return different results for sequential calls
        call_count = [0]

        def side_effect_run(query, params=None):
            call_count[0] += 1
            if call_count[0] == 1:  # total_nodes
                return [{"count": 3257}]
            elif call_count[0] == 2:  # node_types
                return [{"label": "Class", "count": 1500}, {"label": "Package", "count": 500}]
            elif call_count[0] == 3:  # total_relationships
                return [{"count": 10027}]
            else:  # relationship_types
                return [{"type": "CONTAINS", "count": 5000}, {"type": "GENERALIZES", "count": 2000}]

        mock_session.run.side_effect = side_effect_run

        stats = neo4j_service.get_statistics()

        assert stats["total_nodes"] == 3257
        assert stats["total_relationships"] == 10027
        assert "Class" in stats["node_types"]
        assert stats["node_types"]["Class"] == 1500
        assert "CONTAINS" in stats["relationship_types"]

    def test_create_node(self, neo4j_service, mock_driver):
        """Test creating a new node"""
        mock_session = MagicMock()
        mock_result = [{"uid": "uid-new-123"}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        properties = {"name": "NewClass", "comment": "Test class"}
        uid = neo4j_service.create_node("Class", properties)

        assert uid == "uid-new-123"

    def test_update_node(self, neo4j_service, mock_driver):
        """Test updating an existing node"""
        mock_session = MagicMock()
        mock_result = [{"updated": 1}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        updates = {"name": "UpdatedClass", "comment": "Updated comment"}
        result = neo4j_service.update_node("Class", "uid-123", updates)

        assert result is True

    def test_delete_node(self, neo4j_service, mock_driver):
        """Test deleting a node"""
        mock_session = MagicMock()
        mock_result = [{"deleted": 1}]
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        result = neo4j_service.delete_node("Class", "uid-123")

        assert result is True

    def test_execute_write(self, neo4j_service, mock_driver):
        """Test executing a write transaction"""
        mock_session = MagicMock()
        mock_tx = MagicMock()
        mock_result = [{"created": 1}]
        mock_tx.run.return_value = mock_result
        mock_session.execute_write.return_value = mock_result
        mock_driver.session.return_value.__enter__.return_value = mock_session

        query = "CREATE (c:Class {name: $name}) RETURN c"
        params = {"name": "TestClass"}
        result = neo4j_service.execute_write(query, params)

        assert result == mock_result

    def test_close(self, neo4j_service, mock_driver):
        """Test closing the driver connection"""
        neo4j_service.close()
        mock_driver.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
