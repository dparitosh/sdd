"""
Utility classes for FastAPI responses and encoding
"""

import json
from typing import Any

from fastapi.responses import JSONResponse


class Neo4jJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Neo4j types"""
    def default(self, obj):
        if hasattr(obj, "iso_format"):
            return obj.iso_format()
        if hasattr(obj, "isoformat") and not isinstance(obj, str):
            return obj.isoformat()
        return super().default(obj)


class Neo4jJSONResponse(JSONResponse):
    """Custom JSON response class for Neo4j types"""
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=Neo4jJSONEncoder,
        ).encode("utf-8")
