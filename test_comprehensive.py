#!/usr/bin/env python3
"""
Comprehensive Configuration and Connection Test
Validates all aspects of the improved Neo4j service
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_configuration():
    """Test configuration loading"""
    print("=" * 60)
    print("Configuration Test")
    print("=" * 60)
    
    required_vars = [
        "NEO4J_URI",
        "NEO4J_USER", 
        "NEO4J_PASSWORD",
        "NEO4J_DATABASE",
        "API_BASE_URL",
        "FLASK_PORT",
        "FLASK_HOST",
        "VITE_PORT"
    ]
    
    missing = []
    for var in required_vars:
        value = os.getenv(var)
        status = "✓" if value else "✗"
        display_value = value if var not in ["NEO4J_PASSWORD"] else ("*" * 8 if value else "Not set")
        print(f"  {status} {var:20s} = {display_value}")
        if not value:
            missing.append(var)
    
    if missing:
        print(f"\n✗ Missing variables: {', '.join(missing)}")
        return False
    else:
        print("\n✓ All required variables present")
        return True

def test_neo4j_service():
    """Test Neo4j service functionality"""
    print("\n" + "=" * 60)
    print("Neo4j Service Test")
    print("=" * 60)
    
    from src.web.services.neo4j_service import Neo4jService
    
    try:
        # Test 1: Service initialization
        print("\n1. Testing service initialization...")
        service = Neo4jService()
        print("   ✓ Service created")
        
        # Test 2: Lazy driver creation
        print("\n2. Testing lazy driver initialization...")
        driver = service.driver
        print(f"   ✓ Driver created: {type(driver).__name__}")
        
        # Test 3: Connection verification
        print("\n3. Testing connection verification...")
        start = time.time()
        service.verify_connectivity()
        latency = (time.time() - start) * 1000
        print(f"   ✓ Connected in {latency:.2f}ms")
        
        # Test 4: Simple query
        print("\n4. Testing simple query...")
        start = time.time()
        result = service.execute_query("RETURN 1 AS test")
        query_time = (time.time() - start) * 1000
        assert result[0]["test"] == 1
        print(f"   ✓ Query executed in {query_time:.2f}ms")
        
        # Test 5: Node count query
        print("\n5. Testing node count query...")
        start = time.time()
        result = service.execute_query("MATCH (n) RETURN count(n) as count")
        query_time = (time.time() - start) * 1000
        node_count = result[0]["count"]
        print(f"   ✓ Query executed in {query_time:.2f}ms")
        print(f"   ✓ Total nodes: {node_count:,}")
        
        # Test 6: Label query
        print("\n6. Testing label query...")
        result = service.execute_query("CALL db.labels() YIELD label RETURN collect(label) as labels")
        labels = result[0]["labels"]
        print(f"   ✓ Found {len(labels)} labels: {', '.join(labels[:5])}")
        if len(labels) > 5:
            print(f"      ... and {len(labels) - 5} more")
        
        # Test 7: Context manager
        print("\n7. Testing context manager...")
        with Neo4jService() as svc:
            result = svc.execute_query("RETURN 'context_manager_test' AS test")
            assert result[0]["test"] == "context_manager_test"
        print("   ✓ Context manager working")
        
        # Test 8: Error handling
        print("\n8. Testing error handling...")
        try:
            service.execute_query("INVALID CYPHER SYNTAX")
            print("   ✗ Should have raised exception")
            return False
        except Exception as e:
            print(f"   ✓ Proper error handling: {type(e).__name__}")
        
        # Test 9: Database parameter
        print("\n9. Testing database parameter...")
        result = service.execute_query("RETURN 1 AS test", database=service.database)
        assert result[0]["test"] == 1
        print("   ✓ Database parameter working")
        
        # Test 10: Connection close
        print("\n10. Testing connection close...")
        service.close()
        print("   ✓ Connection closed successfully")
        
        print("\n" + "=" * 60)
        print("✓ All Neo4j service tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_singleton_pattern():
    """Test singleton pattern"""
    print("\n" + "=" * 60)
    print("Singleton Pattern Test")
    print("=" * 60)
    
    from src.web.services import get_neo4j_service
    
    print("\n1. Getting first instance...")
    service1 = get_neo4j_service()
    print(f"   ✓ Instance 1: {id(service1)}")
    
    print("\n2. Getting second instance...")
    service2 = get_neo4j_service()
    print(f"   ✓ Instance 2: {id(service2)}")
    
    if service1 is service2:
        print("\n✓ Singleton pattern working (same instance)")
        return True
    else:
        print("\n✗ Singleton pattern broken (different instances)")
        return False

def performance_benchmark():
    """Run performance benchmarks"""
    print("\n" + "=" * 60)
    print("Performance Benchmark")
    print("=" * 60)
    
    from src.web.services.neo4j_service import Neo4jService
    
    service = Neo4jService()
    service.verify_connectivity()
    
    queries = [
        ("Simple return", "RETURN 1 AS test"),
        ("Node count", "MATCH (n) RETURN count(n) as count LIMIT 1"),
        ("Label list", "CALL db.labels() YIELD label RETURN label LIMIT 10"),
        ("Property keys", "CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey LIMIT 10"),
    ]
    
    print("\nQuery Performance:")
    print("-" * 60)
    
    for name, query in queries:
        times = []
        for _ in range(5):
            start = time.time()
            service.execute_query(query)
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
        
        avg = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"  {name:20s}: avg={avg:6.2f}ms  min={min_time:6.2f}ms  max={max_time:6.2f}ms")
    
    service.close()
    print("\n✓ Performance benchmark complete")
    return True

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "MBSE Neo4j Configuration & Connection Test" + " " * 5 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    results = []
    
    # Test 1: Configuration
    results.append(("Configuration", test_configuration()))
    
    # Test 2: Neo4j Service
    if results[0][1]:  # Only if config test passed
        results.append(("Neo4j Service", test_neo4j_service()))
        results.append(("Singleton Pattern", test_singleton_pattern()))
        results.append(("Performance", performance_benchmark()))
    
    # Summary
    print("\n")
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status} - {name}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 18 + "✓ ALL TESTS PASSED!" + " " * 19 + "║")
        print("╚" + "=" * 58 + "╝")
        return 0
    else:
        print("╔" + "=" * 58 + "╗")
        print("║" + " " * 18 + "✗ SOME TESTS FAILED" + " " * 18 + "║")
        print("╚" + "=" * 58 + "╝")
        return 1

if __name__ == "__main__":
    sys.exit(main())
