"""
Unit tests for ApprovalService — Quality Head Sign-off [G5, G6].

Tests use a mock Neo4jPool so no live Neo4j instance is required.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.models.sdd_types import (
    ApprovalRecord,
    ApprovalStatus,
    DecisionLog,
)
from src.functions.approval_service.service import ApprovalService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(read_return=None):
    pool = MagicMock()
    pool.execute_read = MagicMock(return_value=read_return or [])
    return pool


def _approval_row(
    record_id: str = "AR-1",
    dossier_id: str = "DOS-1",
    status: str = "Approved",
    reviewer: str = "Jane Doe",
    comment: str = "Looks good",
    signature_id: str = "SIG-1",
    role: str = "Quality Head",
    timestamp: str | None = None,
):
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "record": {
            "id": record_id,
            "dossier_id": dossier_id,
            "status": status,
            "reviewer": reviewer,
            "comment": comment,
            "signature_id": signature_id,
            "role": role,
            "timestamp": timestamp,
        }
    }


def _decision_row(
    decision_id: str = "DL-1",
    dossier_id: str = "DOS-1",
    status: str = "Approved",
    reviewer: str = "Jane Doe",
    comment: str = "ok",
    signature_id: str = "SIG-1",
    timestamp: str | None = None,
):
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "entry": {
            "id": decision_id,
            "dossier_id": dossier_id,
            "status": status,
            "reviewer": reviewer,
            "comment": comment,
            "signature_id": signature_id,
            "timestamp": timestamp,
        }
    }


# ---------------------------------------------------------------------------
# Tests: approve — happy path
# ---------------------------------------------------------------------------

class TestApproveHappyPath:
    def test_approve_returns_approval_record(self):
        pool = _make_pool(read_return=[_approval_row()])
        svc = ApprovalService(pool=pool)

        result = svc.approve(
            dossier_id="DOS-1",
            status="Approved",
            reviewer="Jane Doe",
            comment="Looks good",
            signature_id="SIG-1",
            role="Quality Head",
        )

        assert isinstance(result, ApprovalRecord)
        assert result.dossier_id == "DOS-1"
        assert result.status == ApprovalStatus.APPROVED
        assert result.reviewer == "Jane Doe"
        assert result.comment == "Looks good"

    def test_approve_rejected(self):
        pool = _make_pool(read_return=[_approval_row(status="Rejected")])
        svc = ApprovalService(pool=pool)

        result = svc.approve(
            dossier_id="DOS-1",
            status="Rejected",
            reviewer="John Smith",
            comment="Insufficient evidence",
        )

        assert result.status == ApprovalStatus.REJECTED

    def test_approve_calls_execute_read_with_params(self):
        pool = _make_pool(read_return=[_approval_row()])
        svc = ApprovalService(pool=pool)

        svc.approve(
            dossier_id="DOS-1",
            status="Approved",
            reviewer="Jane",
        )

        pool.execute_read.assert_called_once()
        args = pool.execute_read.call_args
        params = args[0][1]  # second positional arg = params dict
        assert params["dossier_id"] == "DOS-1"
        assert params["status"] == "Approved"
        assert params["reviewer"] == "Jane"


# ---------------------------------------------------------------------------
# Tests: approve — validation
# ---------------------------------------------------------------------------

class TestApproveValidation:
    def test_invalid_status_raises_value_error(self):
        pool = _make_pool()
        svc = ApprovalService(pool=pool)

        with pytest.raises(ValueError, match="Invalid status"):
            svc.approve(
                dossier_id="DOS-1",
                status="Pending",
                reviewer="Jane",
            )

    def test_dossier_not_found_raises(self):
        pool = _make_pool(read_return=[])
        svc = ApprovalService(pool=pool)

        with pytest.raises(ValueError, match="not found"):
            svc.approve(
                dossier_id="MISSING-1",
                status="Approved",
                reviewer="Jane",
            )


# ---------------------------------------------------------------------------
# Tests: approve — default parameters
# ---------------------------------------------------------------------------

class TestApproveDefaults:
    def test_empty_comment_defaults(self):
        pool = _make_pool(read_return=[_approval_row(comment="")])
        svc = ApprovalService(pool=pool)

        result = svc.approve(
            dossier_id="DOS-1",
            status="Approved",
            reviewer="Jane",
        )

        assert result.comment == ""

    def test_missing_signature_id(self):
        pool = _make_pool(read_return=[_approval_row(signature_id="")])
        svc = ApprovalService(pool=pool)

        result = svc.approve(
            dossier_id="DOS-1",
            status="Approved",
            reviewer="Jane",
        )

        # Empty string converted to None by `or None` in the service
        assert result.signature_id is None


# ---------------------------------------------------------------------------
# Tests: get_history
# ---------------------------------------------------------------------------

class TestGetHistory:
    def test_returns_list_of_decision_logs(self):
        rows = [
            _decision_row(decision_id="DL-1", status="Approved"),
            _decision_row(decision_id="DL-2", status="Rejected"),
        ]
        pool = _make_pool(read_return=rows)
        svc = ApprovalService(pool=pool)

        history = svc.get_history("DOS-1")

        assert len(history) == 2
        assert all(isinstance(h, DecisionLog) for h in history)
        assert history[0].id == "DL-1"
        assert history[1].id == "DL-2"

    def test_empty_history(self):
        pool = _make_pool(read_return=[])
        svc = ApprovalService(pool=pool)

        history = svc.get_history("DOS-1")
        assert history == []

    def test_history_fields_populated(self):
        ts = "2025-01-15T10:30:00+00:00"
        rows = [
            _decision_row(
                decision_id="DL-99",
                dossier_id="DOS-5",
                status="Approved",
                reviewer="Alice",
                comment="Great work",
                signature_id="SIG-42",
                timestamp=ts,
            )
        ]
        pool = _make_pool(read_return=rows)
        svc = ApprovalService(pool=pool)

        history = svc.get_history("DOS-5")

        assert len(history) == 1
        entry = history[0]
        assert entry.id == "DL-99"
        assert entry.dossier_id == "DOS-5"
        assert entry.status == "Approved"
        assert entry.reviewer == "Alice"
        assert entry.comment == "Great work"
        assert entry.signature_id == "SIG-42"
        assert isinstance(entry.timestamp, datetime)
