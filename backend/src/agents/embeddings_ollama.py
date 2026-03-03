import os
from typing import List
import requests


class OllamaEmbeddings:
    """Simple Ollama embeddings wrapper.

    Expects an Ollama HTTP API available at OLLAMA_BASE_URL (default http://localhost:11434)
    and an embedding model name in OLLAMA_EMBED_MODEL (default: nomic-embed-text:latest).
    """

    def __init__(self, base_url: str | None = None, model: str | None = None, timeout: int = 300):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = model or os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text:latest")
        self.timeout = timeout

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Return embeddings for a list of input texts.

        Best-effort parsing of common Ollama embed response shapes is performed.
        """
        if not texts:
            return []

        url = f"{self.base_url.rstrip('/')}/api/embed"
        payload = {"model": self.model, "input": texts}
        resp = requests.post(url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        # Handle multiple response formats used by embedding APIs
        if isinstance(data, dict):
            if "embeddings" in data and isinstance(data["embeddings"], list):
                return data["embeddings"]
            if "data" in data and isinstance(data["data"], list):
                # e.g. OpenAI-style objects
                embeddings = []
                for item in data["data"]:
                    if isinstance(item, dict) and "embedding" in item:
                        embeddings.append(item["embedding"])
                    else:
                        embeddings.append(item)
                return embeddings

        if isinstance(data, list):
            return data

        raise ValueError(f"Unexpected embedding response shape: {type(data)} -> {data}")


__all__ = ["OllamaEmbeddings"]
