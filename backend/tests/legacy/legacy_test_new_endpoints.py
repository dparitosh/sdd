"""
Comprehensive test suite for newly converted FastAPI endpoints
Tests auth, plm, simulation, export, and version routes
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:5000/api"

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class EndpointTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.token = None

    def test_endpoint(
        self,
        name: str,
        method: str,
        url: str,
        expected_status: int = 200,
        data: Dict[Any, Any] = None,
        headers: Dict[str, str] = None,
    ):
        """Test a single endpoint and report results"""
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method == "POST":
                response = requests.post(url, json=data, headers=headers, timeout=10)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code == expected_status:
                print(
                    f"{GREEN}✓{RESET} {name}: {response.status_code} (Expected: {expected_status})"
                )
                self.passed += 1
                return response
            else:
                print(
                    f"{RED}✗{RESET} {name}: {response.status_code} (Expected: {expected_status})"
                )
                print(f"  Response: {response.text[:200]}")
                self.failed += 1
                return None
        except Exception as e:
            print(f"{RED}✗{RESET} {name}: {str(e)}")
            self.failed += 1
            return None

    def print_header(self, title: str):
        """Print section header"""
        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}{title.center(70)}{RESET}")
        print(f"{BLUE}{'='*70}{RESET}\n")

    def print_summary(self):
        """Print test summary"""
        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"\n{BLUE}{'='*70}{RESET}")
        print(f"{BLUE}TEST SUMMARY{RESET}".center(80))
        print(f"{BLUE}{'='*70}{RESET}")
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {self.passed}{RESET}")
        print(f"{RED}Failed: {self.failed}{RESET}")
        print(f"Pass Rate: {pass_rate:.1f}%")
        print(f"{BLUE}{'='*70}{RESET}\n")


def main():
    tester = EndpointTester()

    # Test Health Check First
    tester.print_header("HEALTH CHECK")
    tester.test_endpoint("Health Check", "GET", f"{BASE_URL}/health")

    # Test Authentication Endpoints
    tester.print_header("AUTHENTICATION ENDPOINTS")

    # Test login (should fail with demo credentials)
    response = tester.test_endpoint(
        "Login (Expected Fail)",
        "POST",
        f"{BASE_URL}/auth/login",
        expected_status=401,
        data={"username": "demo", "password": "demo123"},
    )

    # Test verify token (no token)
    tester.test_endpoint(
        "Verify Token (No Auth)", "GET", f"{BASE_URL}/auth/verify", expected_status=401
    )

    # Test PLM Integration Endpoints
    tester.print_header("PLM INTEGRATION ENDPOINTS")

    tester.test_endpoint(
        "PLM Traceability Matrix", "GET", f"{BASE_URL}/plm/traceability"
    )

    tester.test_endpoint("PLM Parameters", "GET", f"{BASE_URL}/plm/parameters?limit=10")

    tester.test_endpoint(
        "PLM Constraints", "GET", f"{BASE_URL}/plm/constraints?limit=10"
    )

    # Test with a node ID (using a common pattern, may 404 if not exists)
    tester.test_endpoint(
        "PLM Composition (404 expected)",
        "GET",
        f"{BASE_URL}/plm/composition/test-node",
        expected_status=404,
    )

    tester.test_endpoint(
        "PLM Impact Analysis (404 expected)",
        "GET",
        f"{BASE_URL}/plm/impact/test-node",
        expected_status=404,
    )

    # Test Simulation Endpoints
    tester.print_header("SIMULATION INTEGRATION ENDPOINTS")

    tester.test_endpoint(
        "Simulation Parameters", "GET", f"{BASE_URL}/simulation/parameters?limit=10"
    )

    tester.test_endpoint("Simulation Units", "GET", f"{BASE_URL}/simulation/units")

    # Test validation endpoint
    tester.test_endpoint(
        "Simulation Validate",
        "POST",
        f"{BASE_URL}/simulation/validate",
        data={"parameters": [{"id": "test-param-1", "value": 100.0}]},
    )

    # Test Export Endpoints
    tester.print_header("EXPORT ENDPOINTS")

    tester.test_endpoint("Export GraphML", "GET", f"{BASE_URL}/export/graphml?limit=5")

    tester.test_endpoint("Export JSON-LD", "GET", f"{BASE_URL}/export/jsonld?limit=5")

    tester.test_endpoint("Export CSV", "GET", f"{BASE_URL}/export/csv?limit=5")

    tester.test_endpoint("Export STEP AP242", "GET", f"{BASE_URL}/export/step?limit=5")

    # Test Version Control Endpoints
    tester.print_header("VERSION CONTROL ENDPOINTS")

    # Test with non-existent node (should 404)
    tester.test_endpoint(
        "Get Versions (404 expected)",
        "GET",
        f"{BASE_URL}/version/versions/test-node",
        expected_status=404,
    )

    tester.test_endpoint(
        "Get History (404 expected)",
        "GET",
        f"{BASE_URL}/version/history/test-node",
        expected_status=404,
    )

    # Test diff endpoint
    tester.test_endpoint(
        "Version Diff (404 expected)",
        "POST",
        f"{BASE_URL}/version/diff",
        expected_status=404,
        data={"node1_id": "test-node-1", "node2_id": "test-node-2"},
    )

    # Test checkpoint creation
    tester.test_endpoint(
        "Create Checkpoint",
        "POST",
        f"{BASE_URL}/version/checkpoint",
        expected_status=201,
        data={"description": "Test checkpoint", "created_by": "test-user"},
    )

    # Test Additional Core Endpoints
    tester.print_header("CORE API ENDPOINTS (Verification)")

    tester.test_endpoint("Get Packages", "GET", f"{BASE_URL}/packages")

    tester.test_endpoint("Get Classes", "GET", f"{BASE_URL}/classes?limit=5")

    tester.test_endpoint("Search", "GET", f"{BASE_URL}/search?q=system")

    tester.test_endpoint("Statistics", "GET", f"{BASE_URL}/stats")

    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    print(f"\n{YELLOW}Starting comprehensive endpoint testing...{RESET}\n")
    print(f"Target: {BASE_URL}")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")

    main()
