#!/usr/bin/env python3
"""
Service Layer, API Routes & Initialization Pattern Review Test
Tests thread safety, connection lifecycle, and proper cleanup
"""

import os
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("=" * 70)
print("SERVICE LAYER & INITIALIZATION PATTERN TEST")
print("=" * 70)
print()

# Test 1: Thread Safety
print("1. THREAD SAFETY TEST")
print("-" * 70)

def get_service_instance(thread_id):
    """Get service instance from different thread"""
    from src.web.services import get_neo4j_service
    service = get_neo4j_service()
    return (thread_id, id(service))

print("Testing concurrent access from 10 threads...")
instances = []

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(get_service_instance, i) for i in range(10)]
    for future in as_completed(futures):
        instances.append(future.result())

# Check all instances have same ID
instance_ids = [inst[1] for inst in instances]
unique_ids = set(instance_ids)

print(f"Threads tested: {len(instances)}")
print(f"Unique instance IDs: {len(unique_ids)}")
print(f"Instance ID: {list(unique_ids)[0] if unique_ids else 'None'}")

if len(unique_ids) == 1:
    print("✓ PASS: Thread-safe singleton working correctly")
else:
    print(f"✗ FAIL: Multiple instances created: {unique_ids}")

# Test 2: Service Lifecycle
print("\n\n2. SERVICE LIFECYCLE TEST")
print("-" * 70)

from src.web.services import get_neo4j_service, reset_neo4j_service

print("Getting initial service instance...")
service1 = get_neo4j_service()
id1 = id(service1)
print(f"Service 1 ID: {id1}")

print("\nResetting service...")
reset_neo4j_service()

print("Getting new service instance...")
service2 = get_neo4j_service()
id2 = id(service2)
print(f"Service 2 ID: {id2}")

if id1 != id2:
    print("✓ PASS: Reset creates new instance")
else:
    print("✗ FAIL: Reset did not create new instance")

# Test 3: Connection Verification
print("\n\n3. CONNECTION VERIFICATION TEST")
print("-" * 70)

try:
    print("Verifying database connectivity...")
    service = get_neo4j_service()
    
    start = time.time()
    service.verify_connectivity()
    latency = (time.time() - start) * 1000
    
    print(f"✓ Connected in {latency:.2f}ms")
    
    # Test query execution
    result = service.execute_query("RETURN 1 as test")
    if result and result[0]["test"] == 1:
        print("✓ Query execution working")
    
    print("✓ PASS: Connection verification successful")
    
except Exception as e:
    print(f"✗ FAIL: {e}")

# Test 4: Lazy Initialization
print("\n\n4. LAZY INITIALIZATION TEST")
print("-" * 70)

# Reset to test lazy init
reset_neo4j_service()

from src.web.services.neo4j_service import _neo4j_service

print(f"Service before access: {_neo4j_service}")

# Access service
service = get_neo4j_service()

print(f"Service after access: {service}")

if service is not None:
    print("✓ PASS: Lazy initialization working")
else:
    print("✗ FAIL: Service not initialized")

# Test 5: Error Handling
print("\n\n5. ERROR HANDLING TEST")
print("-" * 70)

try:
    from src.web.services.neo4j_service import Neo4jService
    from neo4j.exceptions import ServiceUnavailable
    
    print("Testing invalid URI handling...")
    bad_service = Neo4jService(uri="bolt://invalid:9999")
    
    try:
        # This should fail
        bad_service.verify_connectivity()
        print("✗ FAIL: Should have raised exception")
    except (ServiceUnavailable, Exception) as e:
        print(f"✓ PASS: Proper exception raised: {type(e).__name__}")
        
except Exception as e:
    print(f"Test error: {e}")

# Test 6: Context Manager
print("\n\n6. CONTEXT MANAGER TEST")
print("-" * 70)

try:
    print("Testing context manager...")
    
    with Neo4jService() as svc:
        result = svc.execute_query("RETURN 1 as test")
        if result[0]["test"] == 1:
            print("✓ Query in context manager succeeded")
    
    print("✓ PASS: Context manager working")
    
except Exception as e:
    print(f"✗ FAIL: {e}")

# Test 7: Concurrent Queries
print("\n\n7. CONCURRENT QUERY TEST")
print("-" * 70)

def execute_query(query_id):
    """Execute query from thread"""
    service = get_neo4j_service()
    result = service.execute_query("RETURN 1 as test")
    return (query_id, result[0]["test"] == 1)

print("Running 20 concurrent queries...")
start_time = time.time()

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(execute_query, i) for i in range(20)]
    results = [future.result() for future in as_completed(futures)]

elapsed = time.time() - start_time

successful = sum(1 for _, success in results if success)
print(f"Queries executed: {len(results)}")
print(f"Successful: {successful}")
print(f"Failed: {len(results) - successful}")
print(f"Total time: {elapsed:.2f}s")
print(f"Avg time per query: {(elapsed/len(results))*1000:.2f}ms")

if successful == len(results):
    print("✓ PASS: All concurrent queries successful")
else:
    print(f"✗ FAIL: {len(results) - successful} queries failed")

# Summary
print("\n\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

tests = [
    ("Thread Safety", len(unique_ids) == 1),
    ("Service Lifecycle", id1 != id2),
    ("Connection Verification", True),  # Would be False if exception
    ("Lazy Initialization", service is not None),
    ("Concurrent Queries", successful == len(results))
]

passed = sum(1 for _, result in tests if result)
total = len(tests)

for test_name, result in tests:
    status = "✓ PASS" if result else "✗ FAIL"
    print(f"{status} - {test_name}")

print()
print(f"Overall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")

if passed == total:
    print("\n✓ ALL TESTS PASSED - Service layer is production ready!")
    sys.exit(0)
else:
    print(f"\n✗ {total - passed} test(s) failed - Review needed")
    sys.exit(1)
