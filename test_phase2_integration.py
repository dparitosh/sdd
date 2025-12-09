#!/usr/bin/env python3
"""
Comprehensive Phase 2 integration test suite
Tests all new features: PLM connectors, security, monitoring, export
"""

import sys
import os
import asyncio
import time
from typing import Dict, Any

sys.path.insert(0, os.path.abspath('.'))

# Test imports
from src.web.middleware.security_utils import (
    PasswordHasher, TokenManager, RateLimiter, sanitize_input
)
from src.web.middleware.metrics import MetricsCollector
from src.integrations.base_connector import PLMConfig, PLMSystem


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.total = 0
        self.failures = []
    
    def record(self, test_name: str, passed: bool, error: str = ""):
        self.total += 1
        if passed:
            self.passed += 1
            print(f"   ✓ {test_name}")
        else:
            self.failed += 1
            self.failures.append((test_name, error))
            print(f"   ✗ {test_name}: {error}")
    
    def summary(self):
        percentage = (self.passed / self.total * 100) if self.total > 0 else 0
        print(f"\n{'='*60}")
        print(f"TEST RESULTS: {self.passed}/{self.total} passed ({percentage:.0f}%)")
        print(f"{'='*60}")
        
        if self.failures:
            print("\nFailed Tests:")
            for name, error in self.failures:
                print(f"  ✗ {name}")
                print(f"    {error}")
        
        return self.failed == 0


def test_security_features(results: TestResults):
    """Test all security features"""
    print("\n" + "="*60)
    print("TESTING SECURITY FEATURES")
    print("="*60)
    
    try:
        # Test 1: Password hashing
        password = "test_password_123"
        hashed = PasswordHasher.hash_password(password)
        results.record(
            "Password hashing",
            len(hashed) > 50 and hashed.startswith('$2b$')
        )
        
        # Test 2: Password verification (correct)
        is_valid = PasswordHasher.verify_password(password, hashed)
        results.record("Password verification (valid)", is_valid)
        
        # Test 3: Password verification (incorrect)
        is_invalid = PasswordHasher.verify_password("wrong_password", hashed)
        results.record("Password verification (invalid)", not is_invalid)
        
        # Test 4: Token generation
        token = TokenManager.generate_token(32)
        results.record("Token generation", len(token) == 64)  # hex = 2x bytes
        
        # Test 5: API key generation
        api_key = TokenManager.generate_api_key()
        results.record("API key generation", api_key.startswith('mbse_'))
        
        # Test 6: Input sanitization
        dirty = '<script>alert("XSS")</script>Test'
        clean = sanitize_input(dirty)
        results.record("Input sanitization", '<script>' not in clean)
        
        # Test 7: Rate limiting
        limiter = RateLimiter()
        allowed_count = sum(
            1 for _ in range(105)
            if limiter.is_allowed("test_ip", 100, 60)
        )
        results.record("Rate limiting", allowed_count == 100)
        
    except Exception as e:
        results.record("Security tests", False, str(e))


def test_metrics_collection(results: TestResults):
    """Test Prometheus metrics"""
    print("\n" + "="*60)
    print("TESTING METRICS COLLECTION")
    print("="*60)
    
    try:
        # Test 1: Cache metrics
        MetricsCollector.record_cache_hit('test_cache')
        MetricsCollector.record_cache_miss('test_cache')
        results.record("Cache metrics recording", True)
        
        # Test 2: Connection metrics
        MetricsCollector.set_active_connections(10)
        results.record("Connection metrics", True)
        
        # Test 3: PLM sync metrics
        MetricsCollector.record_plm_sync('teamcenter', 'push', True, 1.5)
        results.record("PLM sync metrics", True)
        
    except Exception as e:
        results.record("Metrics tests", False, str(e))


def test_export_service(results: TestResults):
    """Test export service"""
    print("\n" + "="*60)
    print("TESTING EXPORT SERVICE")
    print("="*60)
    
    try:
        from src.web.services.export_service import ExportService
        from src.web.services import get_neo4j_service
        
        neo4j_service = get_neo4j_service()
        export_service = ExportService(neo4j_service)
        
        query = "MATCH (n) RETURN n.name as name LIMIT 5"
        
        # Test 1: JSON export
        json_result = export_service.export_json(query)
        results.record("JSON export", len(json_result) > 0)
        
        # Test 2: CSV export
        csv_result = export_service.export_csv(query)
        results.record("CSV export", len(csv_result) > 0)
        
        # Test 3: XML export
        xml_result = export_service.export_xml(query)
        results.record("XML export", 'xml' in xml_result.lower())
        
        # Test 4: PlantUML export
        plantuml_result = export_service.export_plantuml()
        results.record("PlantUML export", '@startuml' in plantuml_result)
        
        # Test 5: Cytoscape export
        cyto_result = export_service.export_cytoscape()
        results.record(
            "Cytoscape export",
            'elements' in cyto_result and isinstance(cyto_result['elements'], list)
        )
        
    except Exception as e:
        results.record("Export service", False, str(e))


async def test_plm_connectors(results: TestResults):
    """Test PLM connector framework"""
    print("\n" + "="*60)
    print("TESTING PLM CONNECTORS")
    print("="*60)
    
    try:
        from src.integrations.teamcenter_connector import TeamcenterConnector
        from src.integrations.windchill_connector import WindchillConnector
        from src.integrations.sap_odata_connector import SAPODataConnector
        
        # Test 1: Teamcenter connector initialization
        tc_config = PLMConfig(
            system_type=PLMSystem.TEAMCENTER,
            base_url='https://test.teamcenter.com',
            username='test',
            password='test'
        )
        tc_connector = TeamcenterConnector(tc_config)
        results.record("Teamcenter connector init", tc_connector is not None)
        
        # Test 2: Windchill connector initialization
        wc_config = PLMConfig(
            system_type=PLMSystem.WINDCHILL,
            base_url='https://test.windchill.com',
            username='test',
            password='test'
        )
        wc_connector = WindchillConnector(wc_config)
        results.record("Windchill connector init", wc_connector is not None)
        
        # Test 3: SAP connector initialization
        sap_config = PLMConfig(
            system_type=PLMSystem.SAP_PLM,
            base_url='https://test.sap.com',
            username='test',
            password='test'
        )
        sap_connector = SAPODataConnector(sap_config)
        results.record("SAP OData connector init", sap_connector is not None)
        
        # Test 4: Connector factory
        from src.integrations.base_connector import PLMConnectorFactory
        
        registered_systems = [
            PLMSystem.TEAMCENTER,
            PLMSystem.WINDCHILL,
            PLMSystem.SAP_PLM
        ]
        
        all_registered = all(
            PLMConnectorFactory.create(PLMConfig(
                system_type=system,
                base_url='https://test.com',
                username='test',
                password='test'
            )) is not None
            for system in registered_systems
        )
        results.record("PLM connector factory", all_registered)
        
    except Exception as e:
        results.record("PLM connectors", False, str(e))


def test_oauth_authentication(results: TestResults):
    """Test OAuth2/OIDC authentication module"""
    print("\n" + "="*60)
    print("TESTING OAUTH AUTHENTICATION")
    print("="*60)
    
    try:
        from src.web.middleware.oauth_auth import OIDCAuthenticator
        from flask import Flask
        
        # Test 1: Authenticator initialization
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'test-secret-key'
        
        oidc_auth = OIDCAuthenticator(app)
        results.record("OIDC authenticator init", oidc_auth is not None)
        
        # Test 2: JWT generation (mock user)
        import jwt
        
        test_user = {
            'id': 'test-123',
            'email': 'test@company.com',
            'name': 'Test User',
            'provider': 'azure'
        }
        
        token = oidc_auth._generate_jwt(test_user)
        results.record("JWT token generation", len(token) > 0)
        
        # Test 3: JWT verification
        payload = oidc_auth.verify_token(token)
        results.record(
            "JWT token verification",
            payload is not None and payload['email'] == test_user['email']
        )
        
        # Test 4: Role assignment
        roles = oidc_auth._get_user_roles('test@company.com')
        results.record("User role assignment", 'viewer' in roles)
        
    except Exception as e:
        results.record("OAuth authentication", False, str(e))


def test_websocket_handler(results: TestResults):
    """Test WebSocket support"""
    print("\n" + "="*60)
    print("TESTING WEBSOCKET HANDLER")
    print("="*60)
    
    try:
        from flask import Flask
        from flask_socketio import SocketIO
        from src.web.middleware.websocket_handler import GraphUpdateNotifier
        
        # Test 1: WebSocket initialization
        app = Flask(__name__)
        socketio = SocketIO(app)
        notifier = GraphUpdateNotifier(socketio)
        results.record("WebSocket notifier init", notifier is not None)
        
        # Test 2: Connection stats
        stats = notifier.get_connection_stats()
        results.record(
            "WebSocket connection stats",
            'active_connections' in stats
        )
        
    except Exception as e:
        results.record("WebSocket handler", False, str(e))


def test_docker_configuration(results: TestResults):
    """Test Docker configuration files"""
    print("\n" + "="*60)
    print("TESTING DOCKER CONFIGURATION")
    print("="*60)
    
    try:
        import os
        
        # Test 1: Dockerfile exists
        results.record(
            "Dockerfile exists",
            os.path.exists('Dockerfile')
        )
        
        # Test 2: Frontend Dockerfile exists
        results.record(
            "Frontend Dockerfile exists",
            os.path.exists('Dockerfile.frontend')
        )
        
        # Test 3: docker-compose.prod.yml exists
        results.record(
            "docker-compose.prod.yml exists",
            os.path.exists('docker-compose.prod.yml')
        )
        
        # Test 4: nginx config exists
        results.record(
            "nginx config exists",
            os.path.exists('docker/nginx.conf')
        )
        
    except Exception as e:
        results.record("Docker configuration", False, str(e))


def main():
    """Run all Phase 2 integration tests"""
    print("\n" + "="*60)
    print("PHASE 2 COMPREHENSIVE INTEGRATION TESTS")
    print("="*60)
    
    results = TestResults()
    
    # Run all test suites
    test_security_features(results)
    test_metrics_collection(results)
    test_export_service(results)
    
    # Run async tests
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_plm_connectors(results))
    
    test_oauth_authentication(results)
    test_websocket_handler(results)
    test_docker_configuration(results)
    
    # Print summary
    success = results.summary()
    
    if success:
        print("\n🎉 All Phase 2 features passed integration testing!")
        return 0
    else:
        print("\n⚠️  Some Phase 2 features need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
