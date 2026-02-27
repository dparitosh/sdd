"""Approval service business logic — Quality Head Sign-off [G5, G6].

Implements:
  - ``approve(dossier_id, ...)`` — create immutable ``ApprovalRecord`` + ``DecisionLog``
  - ``get_history(dossier_id)`` — return decision log ordered by timestamp
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.database import get_pool, Neo4jPool
from src.core.models.sdd_types import (
    ApprovalRecord,
    ApprovalStatus,
    DecisionLog,
    DossierStatus,
)

# Mapping from approval decision to dossier status
_DECISION_TO_DOSSIER_STATUS = {
    "Approved": DossierStatus.APPROVED.value,
    "Rejected": DossierStatus.REJECTED.value,
}


class ApprovalService:
    """Quality Head sign-off workflow.

    Uses ``core.database.Neo4jPool`` for all graph queries.
    """

    def __init__(self, pool: Optional[Neo4jPool] = None) -> None:
        self._pool = pool or get_pool()

    # ------------------------------------------------------------------
    # approve
    # ------------------------------------------------------------------

    def approve(
        self,
        dossier_id: str,
        status: str,
        reviewer: str,
        comment: str = "",
        signature_id: Optional[str] = None,
        role: str = "",
    ) -> ApprovalRecord:
        """Create an immutable approval record + decision log for a dossier.

        Business rules:
          1. ``status`` must be "Approved" or "Rejected".
          2. Creates an ``ApprovalRecord`` node (immutable — no updates allowed).
          3. Creates a ``DecisionLog`` node.
          4. Links both to the dossier via ``[:HAS_APPROVAL]`` / ``[:HAS_DECISION]``.
          5. Updates the dossier status (Draft/UnderReview -> Approved/Rejected).
        """
        if status not in _DECISION_TO_DOSSIER_STATUS:
            raise ValueError(
                f"Invalid status '{status}'. Must be 'Approved' or 'Rejected'."
            )

        record_id = str(uuid.uuid4())
        decision_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        new_dossier_status = _DECISION_TO_DOSSIER_STATUS[status]

        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})

        // Create immutable ApprovalRecord
        CREATE (ar:ApprovalRecord {
            id:           $record_id,
            status:       $status,
            reviewer:     $reviewer,
            comment:      $comment,
            signature_id: $signature_id,
            role:         $role,
            timestamp:    datetime($now)
        })
        CREATE (d)-[:HAS_APPROVAL]->(ar)

        // Create DecisionLog
        CREATE (dl:DecisionLog {
            id:           $decision_id,
            status:       $status,
            reviewer:     $reviewer,
            comment:      $comment,
            signature_id: $signature_id,
            timestamp:    datetime($now)
        })
        CREATE (d)-[:HAS_DECISION]->(dl)

        // Update dossier status
        SET d.status       = $new_dossier_status,
            d.last_updated = datetime()

        RETURN {
            id:           ar.id,
            dossier_id:   d.id,
            status:       ar.status,
            reviewer:     ar.reviewer,
            comment:      ar.comment,
            signature_id: ar.signature_id,
            role:         ar.role,
            timestamp:    toString(ar.timestamp)
        } AS record
        """

        params = {
            "dossier_id": dossier_id,
            "record_id": record_id,
            "decision_id": decision_id,
            "status": status,
            "reviewer": reviewer,
            "comment": comment,
            "signature_id": signature_id or "",
            "role": role,
            "now": now,
            "new_dossier_status": new_dossier_status,
        }

        rows = self._pool.execute_read(query, params)
        if not rows:
            raise ValueError(f"Dossier '{dossier_id}' not found.")

        rec = rows[0]["record"]
        logger.info(
            f"Approval recorded for dossier {dossier_id}: "
            f"{status} by {reviewer} (record={record_id})"
        )

        return ApprovalRecord(
            id=rec["id"],
            dossier_id=rec["dossier_id"],
            status=ApprovalStatus(rec["status"]),
            reviewer=rec["reviewer"],
            comment=rec.get("comment", ""),
            signature_id=rec.get("signature_id") or None,
            role=rec.get("role", ""),
            timestamp=datetime.fromisoformat(rec["timestamp"]),
        )

    # ------------------------------------------------------------------
    # history
    # ------------------------------------------------------------------

    def get_history(self, dossier_id: str) -> List[DecisionLog]:
        """Return all ``DecisionLog`` nodes for a dossier, newest first."""
        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})-[:HAS_DECISION]->(dl:DecisionLog)
        RETURN {
            id:           dl.id,
            dossier_id:   d.id,
            status:       dl.status,
            reviewer:     dl.reviewer,
            comment:      dl.comment,
            signature_id: dl.signature_id,
            timestamp:    toString(dl.timestamp)
        } AS entry
        ORDER BY dl.timestamp DESC
        """
        rows = self._pool.execute_read(query, {"dossier_id": dossier_id})
        results: List[DecisionLog] = []
        for row in rows:
            e = row["entry"]
            results.append(
                DecisionLog(
                    id=e["id"],
                    dossier_id=e["dossier_id"],
                    status=e["status"],
                    reviewer=e["reviewer"],
                    comment=e.get("comment", ""),
                    signature_id=e.get("signature_id") or None,
                    timestamp=datetime.fromisoformat(e["timestamp"]),
                )
            )
        return results
