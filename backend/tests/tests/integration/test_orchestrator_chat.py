"""
Integration test for the orchestrator chat endpoint.

This test posts a small request to the running backend at http://127.0.0.1:5000
and asserts a successful response. If a 500 is returned the test will fail and
print the response body for debugging.
"""

import requests
import pytest


BASE = "http://127.0.0.1:5000"
ENDPOINT = f"{BASE}/api/agents/orchestrator/run"


def test_orchestrator_chat_returns_200():
    payload = {
        "query": "Unit test: simple knowledge query",
        "task_type": "impact_analysis",
        "mode": "baseline",
    }

    resp = requests.post(ENDPOINT, json=payload, timeout=60)

    # If backend returned 500, include response body for debugging
    if resp.status_code >= 500:
        pytest.fail(f"Orchestrator returned {resp.status_code}: {resp.text}")

    assert resp.status_code == 200, f"Unexpected status: {resp.status_code} -- {resp.text}"
