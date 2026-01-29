"""src.web.middleware.websocket_handler

DEPRECATED (legacy real-time updates).

The backend is FastAPI-based.
If real-time updates are needed, implement them using FastAPI WebSockets
(`fastapi.WebSocket`) or an ASGI Socket.IO server.

This module is intentionally kept as a placeholder to avoid import-time
dependencies on legacy libraries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class GraphUpdateNotifier:
    """Placeholder implementation.

    This exists only to keep old imports from breaking. It does not provide any
    runtime functionality.
    """

    def notify_node_created(self, node_data: Dict[str, Any], room: str = "default") -> None:  # noqa: ARG002
        raise NotImplementedError("GraphUpdateNotifier is not implemented for FastAPI")

    def notify_node_updated(self, node_data: Dict[str, Any], room: str = "default") -> None:  # noqa: ARG002
        raise NotImplementedError("GraphUpdateNotifier is not implemented for FastAPI")

    def notify_node_deleted(self, node_id: str, room: str = "default") -> None:  # noqa: ARG002
        raise NotImplementedError("GraphUpdateNotifier is not implemented for FastAPI")

    def notify_relationship_created(self, rel_data: Dict[str, Any], room: str = "default") -> None:  # noqa: ARG002
        raise NotImplementedError("GraphUpdateNotifier is not implemented for FastAPI")

    def notify_batch_update(self, updates: List[Dict[str, Any]], room: str = "default") -> None:  # noqa: ARG002
        raise NotImplementedError("GraphUpdateNotifier is not implemented for FastAPI")

    def get_connection_stats(self) -> Dict[str, Any]:
        return {"active_connections": 0, "total_rooms": 0, "connections": []}


__all__ = ["GraphUpdateNotifier"]

