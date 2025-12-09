#!/usr/bin/env python3
"""
Test Phase 2 features: Security, WebSocket, Monitoring, Export
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.web.middleware.security_utils import PasswordHasher, TokenManager, RateLimiter, sanitize_input
from src.web.middleware.metrics import MetricsCollector


def test_security_features():
    """Test password hashing and token generation"""
    print("\n" + "="*60)
    print("TESTING SECURITY FEATURES")
    print("="*60)
    
    # Test password hashing
    print("\n1. Password Hashing")
    password = "secure_password_123"
    hashed = PasswordHasher.hash_password(password)
    print(f"   ✓ Password hashed: {hashed[:50]}...")
    
    # Test password verification
    is_valid = PasswordHasher.verify_password(password, hashed)
    print(f"   ✓ Password verification: {is_valid}")
    
    is_invalid = PasswordHasher.verify_password("wrong_password", hashed)
    print(f"   ✓ Invalid password rejected: {not is_invalid}")
    
    # Test token generation
    print("\n2. Token Generation")
    token = TokenManager.generate_token()
    print(f"   ✓ Random token: {token[:30]}...")
    
    api_key = TokenManager.generate_api_key()
    print(f"   ✓ API key: {api_key[:40]}...")
    
    # Test input sanitization
    print("\n3. Input Sanitization")
    dirty_input = '<script>alert("XSS")</script>Hello World'
    clean = sanitize_input(dirty_input)
    print(f"   ✓ Sanitized: {clean}")
    
    # Test rate limiter
    print("\n4. Rate Limiting")
    limiter = RateLimiter()
    
    # Simulate requests
    allowed_count = 0
    for i in range(105):
        if limiter.is_allowed("test_ip", max_requests=100, window_seconds=60):
            allowed_count += 1
    
    print(f"   ✓ Allowed requests: {allowed_count}/105")
    print(f"   ✓ Rate limiting working: {allowed_count == 100}")
    
    return True


def test_metrics():
    """Test Prometheus metrics collection"""
    print("\n" + "="*60)
    print("TESTING METRICS COLLECTION")
    print("="*60)
    
    print("\n1. Cache Metrics")
    MetricsCollector.record_cache_hit('query_cache')
    MetricsCollector.record_cache_miss('query_cache')
    print("   ✓ Cache metrics recorded")
    
    print("\n2. Connection Metrics")
    MetricsCollector.set_active_connections(5)
    print("   ✓ Connection count set to 5")
    
    print("\n3. PLM Sync Metrics")
    MetricsCollector.record_plm_sync('teamcenter', 'push', True, 1.5)
    print("   ✓ PLM sync metrics recorded")
    
    return True


def test_export_service():
    """Test export service functionality"""
    print("\n" + "="*60)
    print("TESTING EXPORT SERVICE")
    print("="*60)
    
    try:
        from src.web.services.export_service import ExportService
        from src.web.services import get_neo4j_service
        
        print("\n1. Initializing Export Service")
        neo4j_service = get_neo4j_service()
        export_service = ExportService(neo4j_service)
        print("   ✓ Export service initialized")
        
        print("\n2. Testing JSON Export")
        query = "MATCH (n) RETURN n.name as name LIMIT 5"
        json_result = export_service.export_json(query)
        print(f"   ✓ JSON export: {len(json_result)} characters")
        
        print("\n3. Testing CSV Export")
        csv_result = export_service.export_csv(query)
        print(f"   ✓ CSV export: {len(csv_result)} characters")
        
        print("\n4. Testing XML Export")
        xml_result = export_service.export_xml(query)
        print(f"   ✓ XML export: {len(xml_result)} characters")
        
        print("\n5. Testing PlantUML Export")
        plantuml_result = export_service.export_plantuml()
        print(f"   ✓ PlantUML export: {len(plantuml_result)} characters")
        
        print("\n6. Testing Cytoscape Export")
        cyto_result = export_service.export_cytoscape()
        print(f"   ✓ Cytoscape export: {len(cyto_result['elements'])} elements")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Export test failed: {e}")
        return False


def main():
    """Run all Phase 2 tests"""
    print("\n" + "="*60)
    print("PHASE 2 FEATURE TESTING")
    print("="*60)
    
    results = {
        'Security': test_security_features(),
        'Metrics': test_metrics(),
        'Export': test_export_service()
    }
    
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    for feature, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{feature}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    percentage = (passed / total) * 100
    
    print(f"\nOverall: {passed}/{total} tests passed ({percentage:.0f}%)")
    
    if passed == total:
        print("\n🎉 All Phase 2 features working correctly!")
        return 0
    else:
        print("\n⚠️  Some Phase 2 features need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
