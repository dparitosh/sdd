"""
Integration Tests for MBSE Knowledge Graph API
Tests full workflows and endpoint interactions
"""

import json
from typing import Any, Dict

import pytest
import requests

# Base URL for API
BASE_URL = "http://127.0.0.1:5000"
API_V1 = f"{BASE_URL}/api/v1"
API_CORE = f"{BASE_URL}/api"


@pytest.fixture
def api_client():
    """Fixture to provide API client configuration"""
    return {
        "base_url": BASE_URL,
        "v1_url": API_V1,
        "core_url": API_CORE,
        "headers": {"Content-Type": "application/json"},
    }


@pytest.fixture
def sample_class_id(api_client):
    """Fixture to get a sample Class ID for testing"""
    response = requests.get(f"{api_client['v1_url']}/Class", params={"limit": 1})
    assert response.status_code == 200
    data = response.json()
    if data.get("resources") and len(data["resources"]) > 0:
        return data["resources"][0]["uid"]
    pytest.skip("No Class nodes available for testing")


@pytest.fixture
def sample_requirement_id():
    """Fixture to provide a sample requirement ID"""
    return "_REQ_PERF_002"  # Created by sample data script


class TestHealthCheck:
    """Test system health and connectivity"""

    def test_health_endpoint(self, api_client):
        """Test /health endpoint returns 200"""
        response = requests.get(f"{api_client['v1_url']}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_stats_endpoint(self, api_client):
        """Test /api/stats returns database statistics"""
        response = requests.get(f"{api_client['core_url']}/stats")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "relationships" in data
        assert data["nodes"] > 0


class TestCoreAPIWorkflows:
    """Test Core CRUD API workflows"""

    def test_list_classes(self, api_client):
        """Test listing classes with pagination"""
        response = requests.get(f"{api_client['v1_url']}/Class", params={"limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert "resources" in data
        assert isinstance(data["resources"], list)

    def test_get_class_details(self, api_client, sample_class_id):
        """Test getting class details by ID"""
        response = requests.get(
            f"{api_client['core_url']}/artifacts/Class/{sample_class_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_class_id
        assert "name" in data
        assert "properties" in data

    def test_search_functionality(self, api_client):
        """Test search endpoint with query"""
        response = requests.post(
            f"{api_client['core_url']}/search", json={"name": "System", "limit": 5}
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data or isinstance(data, list)

    def test_cypher_query(self, api_client):
        """Test custom Cypher query execution"""
        query = "MATCH (n:Class) RETURN n.name as name LIMIT 3"
        response = requests.post(
            f"{api_client['core_url']}/cypher", json={"query": query}
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data or isinstance(data, list)


class TestPLMWorkflows:
    """Test PLM Integration workflows"""

    def test_traceability_matrix(self, api_client):
        """Test requirements traceability matrix"""
        response = requests.get(
            f"{api_client['v1_url']}/traceability", params={"depth": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert "traceability" in data
        assert "total" in data
        assert isinstance(data["traceability"], list)

    def test_traceability_filtered(self, api_client):
        """Test traceability with filters"""
        response = requests.get(
            f"{api_client['v1_url']}/traceability",
            params={"source_type": "Requirement", "target_type": "Class", "depth": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert "filters" in data
        assert data["filters"]["source_type"] == "Requirement"

    def test_composition_hierarchy(self, api_client, sample_class_id):
        """Test BOM composition hierarchy"""
        response = requests.get(
            f"{api_client['v1_url']}/composition/{sample_class_id}", params={"depth": 5}
        )
        # May return 404 if no composition exists, which is okay
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "root" in data
            assert "children" in data

    def test_impact_analysis(self, api_client, sample_class_id):
        """Test change impact analysis"""
        response = requests.get(
            f"{api_client['v1_url']}/impact/{sample_class_id}", params={"depth": 3}
        )
        assert response.status_code == 200
        data = response.json()
        assert "node" in data
        assert "upstream_impact" in data
        assert "downstream_impact" in data
        assert "total_impact" in data

    def test_parameters_extraction(self, api_client):
        """Test parameter extraction"""
        response = requests.get(
            f"{api_client['v1_url']}/parameters", params={"limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "parameters" in data
        assert "total" in data
        assert isinstance(data["parameters"], list)

    def test_constraints_retrieval(self, api_client):
        """Test constraints retrieval"""
        response = requests.get(
            f"{api_client['v1_url']}/constraints", params={"limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "constraints" in data
        assert "total" in data


class TestSimulationWorkflows:
    """Test Simulation Integration workflows"""

    def test_simulation_parameters(self, api_client):
        """Test simulation parameter extraction"""
        response = requests.get(
            f"{api_client['v1_url']}/simulation/parameters", params={"limit": 10}
        )
        assert response.status_code == 200
        data = response.json()
        assert "parameters" in data
        assert "total" in data

    def test_simulation_parameters_filtered(self, api_client):
        """Test filtered simulation parameters"""
        response = requests.get(
            f"{api_client['v1_url']}/simulation/parameters",
            params={"include_constraints": "true", "limit": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "filters" in data

    def test_parameter_validation(self, api_client):
        """Test parameter validation"""
        validation_request = {
            "parameters": [
                {"id": "test_param_1", "value": 100},
                {"id": "test_param_2", "value": [1, 2, 3]},
            ]
        }
        response = requests.post(
            f"{api_client['v1_url']}/simulation/validate", json=validation_request
        )
        # May return validation errors, which is expected
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = response.json()
            assert "results" in data
            assert "total_parameters" in data

    def test_units_retrieval(self, api_client):
        """Test units/datatypes retrieval"""
        response = requests.get(f"{api_client['v1_url']}/simulation/units")
        assert response.status_code == 200
        data = response.json()
        assert "unit_types" in data
        assert "unit_properties" in data


class TestExportWorkflows:
    """Test Export functionality workflows"""

    def test_graphml_export(self, api_client):
        """Test GraphML XML export"""
        response = requests.get(
            f"{api_client['v1_url']}/export/graphml",
            params={"limit": 100, "include_properties": "true"},
        )
        assert response.status_code == 200
        assert "xml" in response.headers.get("Content-Type", "")
        assert len(response.content) > 0

    def test_jsonld_export(self, api_client):
        """Test JSON-LD export"""
        response = requests.get(
            f"{api_client['v1_url']}/export/jsonld", params={"limit": 100}
        )
        assert response.status_code == 200
        assert "json" in response.headers.get("Content-Type", "")
        data = response.json()
        assert "@context" in data
        assert "@graph" in data

    def test_csv_export(self, api_client):
        """Test CSV export"""
        response = requests.get(
            f"{api_client['v1_url']}/export/csv",
            params={"node_type": "Class", "limit": 50},
        )
        assert response.status_code == 200
        assert "zip" in response.headers.get("Content-Type", "")

    def test_step_export(self, api_client):
        """Test STEP AP242 export"""
        response = requests.get(
            f"{api_client['v1_url']}/export/step", params={"limit": 50}
        )
        assert response.status_code == 200
        assert len(response.content) > 0
        # Check for STEP format markers
        content = response.content.decode("utf-8")
        assert "ISO-10303-21" in content
        assert "HEADER" in content


class TestVersionControlWorkflows:
    """Test Version Control workflows"""

    def test_version_history(self, api_client, sample_class_id):
        """Test version history retrieval"""
        response = requests.get(f"{api_client['v1_url']}/versions/{sample_class_id}")
        assert response.status_code == 200
        data = response.json()
        assert "node_id" in data
        assert "current_version" in data
        assert "version_history" in data

    def test_version_diff(self, api_client, sample_class_id):
        """Test version comparison"""
        # Use same node twice for simplicity (no diff expected)
        diff_request = {"node1_id": sample_class_id, "node2_id": sample_class_id}
        response = requests.post(f"{api_client['v1_url']}/diff", json=diff_request)
        assert response.status_code == 200
        data = response.json()
        assert "node1" in data
        assert "node2" in data
        assert "differences" in data
        assert "summary" in data

    def test_node_history(self, api_client, sample_class_id):
        """Test node audit trail"""
        response = requests.get(f"{api_client['v1_url']}/history/{sample_class_id}")
        assert response.status_code == 200
        data = response.json()
        assert "node_id" in data
        assert "timeline" in data
        assert "statistics" in data

    def test_checkpoint_creation(self, api_client):
        """Test checkpoint/snapshot creation"""
        checkpoint_request = {
            "name": "test_checkpoint",
            "description": "Integration test checkpoint",
        }
        response = requests.post(
            f"{api_client['v1_url']}/checkpoint", json=checkpoint_request
        )
        assert response.status_code == 201
        data = response.json()
        assert "name" in data
        assert "timestamp" in data
        assert "statistics" in data


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows"""

    def test_requirement_to_design_workflow(self, api_client, sample_requirement_id):
        """Test complete requirement → design traceability workflow"""
        # 1. Get requirement details
        response = requests.get(
            f"{api_client['core_url']}/artifacts/Requirement/{sample_requirement_id}"
        )
        if response.status_code == 404:
            pytest.skip("Sample requirement not found - run sample data script first")
        assert response.status_code == 200
        requirement = response.json()
        assert requirement["id"] == sample_requirement_id

        # 2. Get traceability links
        response = requests.get(
            f"{api_client['v1_url']}/traceability",
            params={"source_type": "Requirement"},
        )
        assert response.status_code == 200
        traceability = response.json()
        assert "traceability" in traceability

        # 3. Get design elements (classes)
        if len(traceability["traceability"]) > 0:
            target_id = traceability["traceability"][0]["target"]["id"]
            response = requests.get(
                f"{api_client['core_url']}/artifacts/Class/{target_id}"
            )
            assert response.status_code == 200

    def test_design_to_simulation_workflow(self, api_client, sample_class_id):
        """Test design → simulation parameter workflow"""
        # 1. Get class details
        response = requests.get(
            f"{api_client['core_url']}/artifacts/Class/{sample_class_id}"
        )
        assert response.status_code == 200
        class_data = response.json()

        # 2. Extract parameters
        response = requests.get(f"{api_client['v1_url']}/parameters")
        assert response.status_code == 200
        parameters = response.json()

        # 3. Get simulation parameters
        response = requests.get(f"{api_client['v1_url']}/simulation/parameters")
        assert response.status_code == 200
        sim_params = response.json()

        # 4. Validate (if parameters exist)
        if len(sim_params["parameters"]) > 0:
            param_id = sim_params["parameters"][0]["id"]
            validation_request = {"parameters": [{"id": param_id, "value": 1.0}]}
            response = requests.post(
                f"{api_client['v1_url']}/simulation/validate", json=validation_request
            )
            assert response.status_code in [200, 400]

    def test_full_export_workflow(self, api_client):
        """Test complete export workflow for all formats"""
        formats = [
            ("graphml", {"limit": 50}),
            ("jsonld", {"limit": 50}),
            ("csv", {"node_type": "Class", "limit": 50}),
            ("step", {"limit": 50}),
        ]

        for format_name, params in formats:
            response = requests.get(
                f"{api_client['v1_url']}/export/{format_name}", params=params
            )
            assert response.status_code == 200, f"{format_name} export failed"
            assert len(response.content) > 0, f"{format_name} export is empty"


# Configuration for pytest
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
