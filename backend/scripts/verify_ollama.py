#!/usr/bin/env python3
"""Ollama model pull & embedding / chat verification script.

Usage:
    python backend/scripts/verify_ollama.py

Pre-conditions:
    - Ollama installed and ``ollama serve`` running on http://localhost:11434
    - Models will be pulled automatically if not already present

Actions:
    1. Verify Ollama server is reachable.
    2. Pull required models (nomic-embed-text, llama3).
    3. Test embedding endpoint (768-dim vector).
    4. Test chat endpoint (short prompt).
    5. Print installed model list.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3:latest"
EXPECTED_DIM = 768


def _url(path: str = "") -> str:
    return f"{OLLAMA_BASE_URL}{path}"


# ------------------------------------------------------------------
# 1. Server health
# ------------------------------------------------------------------

def check_server() -> None:
    print("=" * 60)
    print("1. Checking Ollama server …")
    print("=" * 60)
    try:
        resp = requests.get(_url(""), timeout=10)
        if resp.status_code == 200:
            print(f"   ✓ Ollama is running at {OLLAMA_BASE_URL}")
        else:
            print(f"   WARNING: Unexpected status code {resp.status_code}")
    except requests.ConnectionError:
        print(f"   ERROR: Cannot connect to Ollama at {OLLAMA_BASE_URL}")
        print("   Make sure `ollama serve` is running.")
        sys.exit(1)
    print()


# ------------------------------------------------------------------
# 2. Pull models
# ------------------------------------------------------------------

REQUIRED_MODELS = [EMBED_MODEL, CHAT_MODEL]


def pull_models() -> None:
    print("=" * 60)
    print("2. Pulling required models …")
    print("=" * 60)

    # Check which models are already available
    try:
        resp = requests.get(_url("/api/tags"), timeout=10)
        resp.raise_for_status()
        installed = {m["name"].split(":")[0] for m in resp.json().get("models", [])}
    except Exception:
        installed = set()

    for model in REQUIRED_MODELS:
        base_name = model.split(":")[0]
        if base_name in installed:
            print(f"   ✓ {model} already installed — skipping pull")
            continue
        print(f"   Pulling {model} (this may take a while) …")
        try:
            pull_resp = requests.post(
                _url("/api/pull"),
                json={"name": model, "stream": False},
                timeout=600,  # large models can take minutes
            )
            pull_resp.raise_for_status()
            print(f"   ✓ {model} pulled successfully")
        except Exception as exc:
            print(f"   ✗ Failed to pull {model}: {exc}")
            print("   You can pull manually:  ollama pull " + model)
    print()


# ------------------------------------------------------------------
# 3. Test embeddings
# ------------------------------------------------------------------

def test_embeddings() -> None:
    print("=" * 60)
    print(f"3. Testing embeddings ({EMBED_MODEL}) …")
    print("=" * 60)
    payload = {
        "model": EMBED_MODEL,
        "prompt": "MBSE simulation data test embedding",
    }
    try:
        resp = requests.post(_url("/api/embeddings"), json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding", [])
        dim = len(embedding)
        print(f"   Embedding dimension: {dim}")
        if dim == EXPECTED_DIM:
            print(f"   ✓ Matches expected dimension ({EXPECTED_DIM})")
        else:
            print(f"   WARNING: Expected {EXPECTED_DIM}, got {dim}")
        # Show first 5 values as sanity check
        if embedding:
            preview = ", ".join(f"{v:.6f}" for v in embedding[:5])
            print(f"   First 5 values: [{preview}, …]")
    except Exception as exc:
        print(f"   ✗ Embedding test failed: {exc}")
    print()


# ------------------------------------------------------------------
# 4. Test chat
# ------------------------------------------------------------------

def test_chat() -> None:
    print("=" * 60)
    print(f"4. Testing chat ({CHAT_MODEL}) …")
    print("=" * 60)
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "user", "content": "Respond with exactly: OLLAMA_OK"},
        ],
        "stream": False,
    }
    try:
        resp = requests.post(_url("/api/chat"), json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        message = data.get("message", {})
        content = message.get("content", "").strip()
        print(f"   Model response: {content[:200]}")
        if "OLLAMA_OK" in content.upper():
            print("   ✓ Chat model responded correctly")
        else:
            print("   ⚠ Response did not contain expected token (model may still be fine)")
    except Exception as exc:
        print(f"   ✗ Chat test failed: {exc}")
    print()


# ------------------------------------------------------------------
# 5. List installed models
# ------------------------------------------------------------------

def list_models() -> None:
    print("=" * 60)
    print("5. Installed models …")
    print("=" * 60)
    try:
        resp = requests.get(_url("/api/tags"), timeout=10)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        if not models:
            print("   No models installed.")
            return
        print(f"   {'Name':<35} {'Size':<15} {'Modified'}")
        print(f"   {'-'*35} {'-'*15} {'-'*25}")
        for m in models:
            name = m.get("name", "N/A")
            size_gb = m.get("size", 0) / (1024**3)
            modified = m.get("modified_at", "N/A")
            if isinstance(modified, str) and len(modified) > 19:
                modified = modified[:19]
            print(f"   {name:<35} {size_gb:.2f} GB       {modified}")
        print(f"\n   Total models: {len(models)}")
    except Exception as exc:
        print(f"   ✗ Could not list models: {exc}")
    print()


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main() -> None:
    print(f"\nOllama verification — {OLLAMA_BASE_URL}\n")
    check_server()
    pull_models()
    test_embeddings()
    test_chat()
    list_models()
    print("Done — Ollama verification complete.\n")


if __name__ == "__main__":
    main()
