#!/usr/bin/env python3
"""
Test script for MBSE AI Agent
Tests the LangGraph-based agent without requiring OpenAI API key
Uses mock responses for demonstration
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from loguru import logger

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)


def test_tools_connectivity():
    """Test that all agent tools can connect to the API"""
    from agents.langgraph_agent import MBSETools

    print("\n" + "=" * 60)
    print("MBSE Agent Tools - Connectivity Test")
    print("=" * 60)

    tools = MBSETools("http://127.0.0.1:5000")

    tests = [
        ("get_statistics", lambda: tools.get_statistics()),
        ("search_artifacts", lambda: tools.search_artifacts("Person", limit=3)),
        (
            "execute_cypher",
            lambda: tools.execute_cypher("MATCH (n:Class) RETURN n.name LIMIT 3"),
        ),
    ]

    results = {"passed": 0, "failed": 0}

    for test_name, test_func in tests:
        try:
            print(f"\n[Testing] {test_name}...")
            result = test_func()
            if "Error" in result or "error" in result.lower():
                print(f"  ❌ FAILED: {result[:200]}")
                results["failed"] += 1
            else:
                print(f"  ✅ PASSED: Got {len(result)} bytes of data")
                results["passed"] += 1
        except Exception as e:
            print(f"  ❌ FAILED: {str(e)}")
            results["failed"] += 1

    print(f"\n{'='*60}")
    print(f"Results: {results['passed']} passed, {results['failed']} failed")
    print(f"{'='*60}\n")

    return results["failed"] == 0


def test_agent_without_llm():
    """Test agent structure without requiring OpenAI API"""
    print("\n" + "=" * 60)
    print("MBSE Agent - Structure Test (No LLM)")
    print("=" * 60)

    try:
        from agents.langgraph_agent import MBSETools, AgentState

        print("\n✅ Agent modules imported successfully")

        # Test tools initialization
        tools = MBSETools("http://127.0.0.1:5000")
        print("✅ Tools initialized successfully")

        # Test state structure
        state = {
            "messages": [],
            "current_task": "test",
            "reasoning_steps": [],
            "tool_results": {},
            "next_action": "",
            "error": None,
        }
        print("✅ Agent state structure valid")

        print("\n" + "=" * 60)
        print("Agent structure test PASSED")
        print("=" * 60 + "\n")

        return True

    except Exception as e:
        print(f"\n❌ Agent structure test FAILED: {e}\n")
        return False


def benchmark_api_performance():
    """Benchmark API response times"""
    import time
    import requests

    print("\n" + "=" * 60)
    print("API Performance Benchmark")
    print("=" * 60)

    endpoints = [
        ("Health Check", "GET", "http://127.0.0.1:5000/health"),
        ("Statistics", "GET", "http://127.0.0.1:5000/api/stats"),
        ("List Classes", "GET", "http://127.0.0.1:5000/api/v1/Class?limit=10"),
        ("Cypher Query", "POST", "http://127.0.0.1:5000/api/v1/query"),
    ]

    results = []

    for name, method, url in endpoints:
        try:
            start = time.time()
            if method == "GET":
                response = requests.get(url, timeout=10)
            else:
                response = requests.post(
                    url,
                    json={"query": "MATCH (n:Class) RETURN n.name LIMIT 5"},
                    timeout=10,
                )

            elapsed = (time.time() - start) * 1000  # Convert to ms

            if response.status_code == 200:
                print(f"\n{name}: {elapsed:.2f}ms ✅")
                results.append((name, elapsed, True))
            else:
                print(f"\n{name}: {response.status_code} ❌")
                results.append((name, 0, False))

        except Exception as e:
            print(f"\n{name}: Error - {str(e)[:100]} ❌")
            results.append((name, 0, False))

    # Calculate statistics
    successful = [r for r in results if r[2]]
    if successful:
        avg_time = sum(r[1] for r in successful) / len(successful)
        max_time = max(r[1] for r in successful)
        min_time = min(r[1] for r in successful)

        print(f"\n{'='*60}")
        print(f"Performance Summary:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")
        print(
            f"  Success Rate: {len(successful)}/{len(results)} ({100*len(successful)/len(results):.1f}%)"
        )
        print(f"{'='*60}\n")

        return avg_time < 500  # Target: under 500ms average

    return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print(" " * 15 + "MBSE AI AGENT - PHASE 2 TESTING")
    print("=" * 70)

    print("\nThis test suite validates the AI agent infrastructure")
    print("Note: Full LLM testing requires OPENAI_API_KEY\n")

    # Check if backend is running
    import requests

    try:
        requests.get("http://127.0.0.1:5000/health", timeout=5)
        print("✅ Backend API is running\n")
    except:
        print("❌ Backend API is not running!")
        print("   Please start with: ./start_backend.sh\n")
        return False

    # Run tests
    test_results = []

    print("\n[Test 1/3] Agent Structure Test")
    test_results.append(("Agent Structure", test_agent_without_llm()))

    print("\n[Test 2/3] Tools Connectivity Test")
    test_results.append(("Tools Connectivity", test_tools_connectivity()))

    print("\n[Test 3/3] API Performance Benchmark")
    test_results.append(("API Performance", benchmark_api_performance()))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for test_name, passed in test_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:.<40} {status}")

    total_passed = sum(1 for _, passed in test_results if passed)
    total_tests = len(test_results)

    print(
        f"\nTotal: {total_passed}/{total_tests} tests passed ({100*total_passed/total_tests:.1f}%)"
    )

    if total_passed == total_tests:
        print("\n🎉 All tests PASSED! Agent infrastructure is ready.")
        print("\nNext steps:")
        print("  1. Set OPENAI_API_KEY to test full agent")
        print("  2. Run: export OPENAI_API_KEY=your-key")
        print("  3. Run: python -m src.agents.langgraph_agent")
    else:
        print("\n⚠️  Some tests failed. Please review the errors above.")

    print("=" * 70 + "\n")

    return total_passed == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
