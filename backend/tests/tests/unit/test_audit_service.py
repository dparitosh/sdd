"""
Unit tests for AuditService — ISO-CASCO Compliance Audit Engine [G2, G14].

Tests use a mock Neo4jPool so no live Neo4j instance is required.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.core.models.sdd_types import (
    AuditCategory,
    AuditFinding,
    AuditReport,
    AuditSeverity,
    AuditSummary,
    EvidenceCategoryCode,
)
from src.functions.audit_service.service import AuditService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pool(read_side_effect=None, write_side_effect=None):
    pool = MagicMock()
    pool.execute_read = MagicMock(side_effect=read_side_effect)
    pool.execute_write = MagicMock(side_effect=write_side_effect or (lambda *a, **kw: None))
    return pool


def _full_dossier(
    dossier_id: str = "DOS-1",
    categories: list[str] | None = None,
    artifacts: list[dict] | None = None,
):
    """Return a dossier dict as ``_fetch_dossier`` would."""
    if categories is None:
        categories = [e.value for e in EvidenceCategoryCode]  # all 8
    if artifacts is None:
        artifacts = [
            {
                "id": "ART-1",
                "name": "mesh.h5",
                "type": "Mesh",
                "status": "Final",
                "checksum": "a" * 64,
                "size": 1024,
            }
        ]
    return {
        "id": dossier_id,
        "name": "Test Dossier",
        "status": "Draft",
        "engineer": "tester",
        "artifacts": artifacts,
        "evidence_categories": [
            {"id": f"EC-{c}", "label": c, "status": "Complete", "type": c}
            for c in categories
        ],
    }


# ---------------------------------------------------------------------------
# Tests: run_audit — dossier not found
# ---------------------------------------------------------------------------

class TestRunAuditDossierNotFound:
    def test_returns_critical_when_dossier_missing(self):
        pool = _make_pool(read_side_effect=[[], [], []])  # fetch returns empty
        svc = AuditService(pool=pool)
        report = svc.run_audit("MISSING-1")

        assert isinstance(report, AuditReport)
        assert report.dossier_id == "MISSING-1"
        assert report.health_score == 0
        assert len(report.findings) == 1
        assert report.findings[0].severity == AuditSeverity.CRITICAL
        assert report.summary.critical == 1


# ---------------------------------------------------------------------------
# Tests: _check_completeness
# ---------------------------------------------------------------------------

class TestCheckCompleteness:
    def _svc(self):
        return AuditService(pool=_make_pool(read_side_effect=[]))

    def test_all_categories_present(self):
        svc = self._svc()
        dossier = _full_dossier()
        findings = svc._check_completeness(dossier)

        passed = [f for f in findings if f.severity == AuditSeverity.PASS]
        critical = [f for f in findings if f.severity == AuditSeverity.CRITICAL]
        assert len(passed) >= 1
        assert len(critical) == 0

    def test_missing_categories_produce_critical(self):
        svc = self._svc()
        dossier = _full_dossier(categories=["A1", "B1", "C1"])  # missing D1-H1
        findings = svc._check_completeness(dossier)

        critical = [f for f in findings if f.severity == AuditSeverity.CRITICAL]
        assert len(critical) == 5  # D1, E1, F1, G1, H1
        for f in critical:
            assert "missing" in f.message.lower()

    def test_no_artifacts_produces_warning(self):
        svc = self._svc()
        dossier = _full_dossier(artifacts=[])
        findings = svc._check_completeness(dossier)

        warnings = [f for f in findings if f.severity == AuditSeverity.WARNING]
        assert any("no linked artifacts" in w.message.lower() for w in warnings)

    def test_artifacts_present_produces_pass(self):
        svc = self._svc()
        dossier = _full_dossier()
        findings = svc._check_completeness(dossier)

        passed = [f for f in findings if f.severity == AuditSeverity.PASS]
        assert any("artifact" in p.message.lower() for p in passed)

    def test_null_evidence_categories_treated_as_empty(self):
        svc = self._svc()
        dossier = _full_dossier()
        dossier["evidence_categories"] = None
        findings = svc._check_completeness(dossier)

        critical = [f for f in findings if f.severity == AuditSeverity.CRITICAL]
        assert len(critical) == 8  # all missing

    def test_null_artifacts_treated_as_empty(self):
        svc = self._svc()
        dossier = _full_dossier()
        dossier["artifacts"] = None
        findings = svc._check_completeness(dossier)

        warnings = [f for f in findings if f.severity == AuditSeverity.WARNING]
        assert any("no linked artifacts" in w.message.lower() for w in warnings)


# ---------------------------------------------------------------------------
# Tests: _check_integrity
# ---------------------------------------------------------------------------

class TestCheckIntegrity:
    def _svc(self):
        return AuditService(pool=_make_pool(read_side_effect=[]))

    def test_valid_sha256_passes(self):
        svc = self._svc()
        dossier = _full_dossier(artifacts=[
            {"id": "ART-1", "checksum": "a" * 64, "name": "f.h5"},
        ])
        findings = svc._check_integrity(dossier)

        passed = [f for f in findings if f.severity == AuditSeverity.PASS]
        assert len(passed) >= 1
        assert any("valid SHA-256" in p.message for p in passed)

    def test_invalid_checksum_format_warns(self):
        svc = self._svc()
        dossier = _full_dossier(artifacts=[
            {"id": "ART-1", "checksum": "not-hex", "name": "f.h5"},
        ])
        findings = svc._check_integrity(dossier)

        warnings = [f for f in findings if f.severity == AuditSeverity.WARNING]
        assert any("invalid checksum" in w.message.lower() for w in warnings)

    def test_missing_checksum_warns(self):
        svc = self._svc()
        dossier = _full_dossier(artifacts=[
            {"id": "ART-1", "checksum": None, "name": "f.h5"},
        ])
        findings = svc._check_integrity(dossier)

        warnings = [f for f in findings if f.severity == AuditSeverity.WARNING]
        assert any("no checksum" in w.message.lower() for w in warnings)

    def test_no_artifacts_warns(self):
        svc = self._svc()
        dossier = _full_dossier(artifacts=[])
        findings = svc._check_integrity(dossier)

        warnings = [f for f in findings if f.severity == AuditSeverity.WARNING]
        assert any("no artifacts" in w.message.lower() for w in warnings)

    def test_mixed_checksums(self):
        svc = self._svc()
        dossier = _full_dossier(artifacts=[
            {"id": "ART-1", "checksum": "b" * 64, "name": "good.h5"},
            {"id": "ART-2", "checksum": None, "name": "missing.h5"},
            {"id": "ART-3", "checksum": "short", "name": "bad.h5"},
        ])
        findings = svc._check_integrity(dossier)

        assert any(f.severity == AuditSeverity.PASS for f in findings)
        assert any(f.severity == AuditSeverity.WARNING for f in findings)


# ---------------------------------------------------------------------------
# Tests: _check_traceability
# ---------------------------------------------------------------------------

class TestCheckTraceability:
    def test_no_artifacts_critical(self):
        trace_data = [{"trace": {"artifact_count": 0, "linked_req_count": 0, "artifact_ids": [], "requirement_ids": []}}]
        deep_data = [{"deep": {"reachable_nodes": 0, "total_paths": 0}}]
        pool = _make_pool(read_side_effect=[trace_data, deep_data])
        svc = AuditService(pool=pool)
        findings = svc._check_traceability("DOS-1")

        assert any(f.severity == AuditSeverity.CRITICAL for f in findings)
        assert any("no artifacts" in f.message.lower() for f in findings)

    def test_artifacts_but_no_requirements_warns(self):
        trace_data = [{"trace": {"artifact_count": 3, "linked_req_count": 0, "artifact_ids": ["a"], "requirement_ids": []}}]
        deep_data = [{"deep": {"reachable_nodes": 0, "total_paths": 0}}]
        pool = _make_pool(read_side_effect=[trace_data, deep_data])
        svc = AuditService(pool=pool)
        findings = svc._check_traceability("DOS-1")

        assert any(f.severity == AuditSeverity.WARNING for f in findings)
        assert any("none link" in f.message.lower() for f in findings)

    def test_full_trace_passes(self):
        trace_data = [{"trace": {"artifact_count": 2, "linked_req_count": 2, "artifact_ids": ["a1", "a2"], "requirement_ids": ["r1", "r2"]}}]
        deep_data = [{"deep": {"reachable_nodes": 5, "total_paths": 10}}]
        pool = _make_pool(read_side_effect=[trace_data, deep_data])
        svc = AuditService(pool=pool)
        findings = svc._check_traceability("DOS-1")

        passed = [f for f in findings if f.severity == AuditSeverity.PASS]
        assert len(passed) >= 2  # shallow + deep trace pass

    def test_empty_rows_critical(self):
        pool = _make_pool(read_side_effect=[[], []])
        svc = AuditService(pool=pool)
        findings = svc._check_traceability("DOS-1")

        assert any(f.severity == AuditSeverity.CRITICAL for f in findings)


# ---------------------------------------------------------------------------
# Tests: _summarize and _compute_score
# ---------------------------------------------------------------------------

class TestScoringAndSummary:
    def test_summarize_counts(self):
        findings = [
            AuditFinding(id="1", category=AuditCategory.COMPLIANCE, severity=AuditSeverity.CRITICAL, message="c1"),
            AuditFinding(id="2", category=AuditCategory.COMPLIANCE, severity=AuditSeverity.CRITICAL, message="c2"),
            AuditFinding(id="3", category=AuditCategory.INTEGRITY, severity=AuditSeverity.WARNING, message="w1"),
            AuditFinding(id="4", category=AuditCategory.TRACEABILITY, severity=AuditSeverity.PASS, message="p1"),
            AuditFinding(id="5", category=AuditCategory.TRACEABILITY, severity=AuditSeverity.PASS, message="p2"),
        ]
        summary = AuditService._summarize(findings)
        assert summary.critical == 2
        assert summary.warnings == 1
        assert summary.passed == 2

    def test_compute_score_perfect(self):
        summary = AuditSummary(critical=0, warnings=0, passed=10)
        assert AuditService._compute_score(summary) == 100.0

    def test_compute_score_with_criticals(self):
        summary = AuditSummary(critical=3, warnings=0, passed=0)
        # 100 - 3*20 = 40
        assert AuditService._compute_score(summary) == 40.0

    def test_compute_score_with_warnings(self):
        summary = AuditSummary(critical=0, warnings=4, passed=0)
        # 100 - 4*5 = 80
        assert AuditService._compute_score(summary) == 80.0

    def test_compute_score_mixed(self):
        summary = AuditSummary(critical=2, warnings=3, passed=5)
        # 100 - 2*20 - 3*5 = 100 - 40 - 15 = 45
        assert AuditService._compute_score(summary) == 45.0

    def test_compute_score_floor_at_zero(self):
        summary = AuditSummary(critical=10, warnings=10, passed=0)
        # 100 - 200 - 50 = -150 -> 0
        assert AuditService._compute_score(summary) == 0.0


# ---------------------------------------------------------------------------
# Tests: _persist_findings
# ---------------------------------------------------------------------------

class TestPersistFindings:
    def test_persist_calls_execute_write(self):
        pool = _make_pool()
        svc = AuditService(pool=pool)
        findings = [
            AuditFinding(id="F-1", category=AuditCategory.COMPLIANCE, severity=AuditSeverity.PASS, message="ok"),
        ]
        svc._persist_findings("DOS-1", findings)

        pool.execute_write.assert_called_once()
        args, kwargs = pool.execute_write.call_args
        assert "DOS-1" in str(args) or "DOS-1" in str(kwargs)

    def test_persist_skips_empty_findings(self):
        pool = _make_pool()
        svc = AuditService(pool=pool)
        svc._persist_findings("DOS-1", [])

        pool.execute_write.assert_not_called()

    def test_persist_handles_exception_gracefully(self):
        pool = _make_pool(write_side_effect=Exception("DB down"))
        svc = AuditService(pool=pool)
        findings = [
            AuditFinding(id="F-1", category=AuditCategory.COMPLIANCE, severity=AuditSeverity.CRITICAL, message="fail"),
        ]
        # Should not raise — errors are logged
        svc._persist_findings("DOS-1", findings)


# ---------------------------------------------------------------------------
# Tests: full run_audit with mocked pool
# ---------------------------------------------------------------------------

class TestRunAuditIntegrated:
    def _setup_pool_for_full_audit(self):
        """Set up pool mock for a complete audit: fetch + trace x2 + persist."""
        dossier = _full_dossier()
        trace_data = [{"trace": {"artifact_count": 1, "linked_req_count": 1, "artifact_ids": ["ART-1"], "requirement_ids": ["REQ-1"]}}]
        deep_data = [{"deep": {"reachable_nodes": 3, "total_paths": 5}}]

        pool = MagicMock()
        pool.execute_read = MagicMock(side_effect=[
            [{"dossier": dossier}],  # _fetch_dossier
            trace_data,               # _check_traceability (shallow)
            deep_data,                # _check_traceability (deep)
        ])
        pool.execute_write = MagicMock(return_value=None)
        return pool

    def test_full_audit_returns_report(self):
        pool = self._setup_pool_for_full_audit()
        svc = AuditService(pool=pool)
        report = svc.run_audit("DOS-1")

        assert isinstance(report, AuditReport)
        assert report.dossier_id == "DOS-1"
        assert 0 <= report.health_score <= 100
        assert len(report.findings) > 0
        assert isinstance(report.summary, AuditSummary)

    def test_full_audit_persists_findings(self):
        pool = self._setup_pool_for_full_audit()
        svc = AuditService(pool=pool)
        svc.run_audit("DOS-1")

        pool.execute_write.assert_called_once()

    def test_perfect_dossier_gets_high_score(self):
        pool = self._setup_pool_for_full_audit()
        svc = AuditService(pool=pool)
        report = svc.run_audit("DOS-1")

        # All categories present, valid checksum, full trace → should be 100
        assert report.health_score == 100.0
        assert report.summary.critical == 0
