"""
Audit service business logic — ISO-CASCO Compliance Audit Engine [G2, G14].

Implements ``AuditService.run_audit(dossier_id)`` which:
  1. Fetches the dossier and all linked artifacts from Neo4j.
  2. Checks **Completeness** — Are all 8 MoSSEC evidence categories (A1–H1) populated?
  3. Checks **Integrity** — Verifies artifact checksums (SHA-256) if present.
  4. Checks **Traceability** — Walks MOSSEC relationships (depth 7) and verifies chain completeness.
  5. Returns ``AuditReport`` with healthScore, findings, and summary.
  6. Persists each finding as an ``AuditFinding`` node linked via ``[:HAS_FINDING]`` to the dossier.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.database import get_pool, Neo4jPool
from src.core.models.sdd_types import (
    AuditCategory,
    AuditFinding,
    AuditReport,
    AuditSeverity,
    AuditSummary,
    EvidenceCategoryCode,
)


# All 8 required evidence category codes
_REQUIRED_CATEGORIES = {e.value for e in EvidenceCategoryCode}


class AuditService:
    """ISO-CASCO Compliance Audit Engine.

    Uses ``core.database.Neo4jPool`` for all graph queries.
    """

    def __init__(self, pool: Optional[Neo4jPool] = None) -> None:
        self._pool = pool or get_pool()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_audit(self, dossier_id: str) -> AuditReport:
        """Run a full compliance audit on a dossier.

        Steps:
            1. Fetch dossier + artifacts + evidence categories
            2. Check completeness (8 evidence categories)
            3. Check integrity (artifact checksums)
            4. Check traceability (MOSSEC chain depth <= 7)
            5. Score and persist findings
        """
        logger.info(f"Running audit for dossier {dossier_id}")

        dossier = self._fetch_dossier(dossier_id)
        if dossier is None:
            return AuditReport(
                dossier_id=dossier_id,
                health_score=0,
                findings=[
                    AuditFinding(
                        id=str(uuid.uuid4()),
                        category=AuditCategory.COMPLIANCE,
                        severity=AuditSeverity.CRITICAL,
                        message=f"Dossier '{dossier_id}' not found in graph.",
                        requirement="Dossier must exist",
                    )
                ],
                summary=AuditSummary(critical=1, warnings=0, passed=0),
            )

        findings: List[AuditFinding] = []

        # --- Completeness checks ---
        findings.extend(self._check_completeness(dossier))

        # --- Integrity checks ---
        findings.extend(self._check_integrity(dossier))

        # --- Traceability checks ---
        findings.extend(self._check_traceability(dossier_id))

        # --- Score ---
        summary = self._summarize(findings)
        health_score = self._compute_score(summary)

        report = AuditReport(
            dossier_id=dossier_id,
            health_score=health_score,
            findings=findings,
            summary=summary,
        )

        # --- Persist ---
        self._persist_findings(dossier_id, findings)

        logger.info(
            f"Audit complete for {dossier_id}: score={health_score}, "
            f"critical={summary.critical}, warnings={summary.warnings}, "
            f"passed={summary.passed}"
        )
        return report

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_dossier(self, dossier_id: str) -> Optional[Dict[str, Any]]:
        """Fetch dossier + artifacts + evidence categories from Neo4j."""
        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})
        OPTIONAL MATCH (d)-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact)
        OPTIONAL MATCH (d)-[:HAS_EVIDENCE_CATEGORY]->(e:EvidenceCategory)
        WITH d,
             COLLECT(DISTINCT {
                 id: a.id,
                 name: a.name,
                 type: a.type,
                 status: a.status,
                 checksum: a.checksum,
                 size: a.size
             }) AS artifacts,
             COLLECT(DISTINCT {
                 id: e.id,
                 label: e.label,
                 status: e.status,
                 type: e.type
             }) AS evidence_categories
        RETURN {
            id: d.id,
            name: d.name,
            status: d.status,
            engineer: d.engineer,
            artifacts: artifacts,
            evidence_categories: evidence_categories
        } AS dossier
        """
        rows = self._pool.execute_read(query, {"dossier_id": dossier_id})
        if not rows:
            return None
        return rows[0]["dossier"]

    # ------------------------------------------------------------------
    # Check: Completeness (evidence categories A1-H1)
    # ------------------------------------------------------------------

    def _check_completeness(self, dossier: Dict[str, Any]) -> List[AuditFinding]:
        findings: List[AuditFinding] = []

        evidence = dossier.get("evidence_categories") or []
        present_types = {
            e.get("type") or e.get("label", "") for e in evidence if e.get("id")
        }

        missing = _REQUIRED_CATEGORIES - present_types

        if not missing:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.COMPLIANCE,
                    severity=AuditSeverity.PASS,
                    message="All 8 MoSSEC evidence categories (A1-H1) are present.",
                    requirement="Completeness: 8 evidence categories required",
                )
            )
        else:
            for code in sorted(missing):
                findings.append(
                    AuditFinding(
                        id=str(uuid.uuid4()),
                        category=AuditCategory.COMPLIANCE,
                        severity=AuditSeverity.CRITICAL,
                        message=f"Evidence category '{code}' is missing from the dossier.",
                        requirement=f"Completeness: category {code} required",
                    )
                )

        # Artifact count sanity
        artifacts = dossier.get("artifacts") or []
        real_artifacts = [a for a in artifacts if a.get("id")]
        if not real_artifacts:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.COMPLIANCE,
                    severity=AuditSeverity.WARNING,
                    message="Dossier has no linked artifacts.",
                    requirement="At least one artifact expected",
                )
            )
        else:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.COMPLIANCE,
                    severity=AuditSeverity.PASS,
                    message=f"Dossier has {len(real_artifacts)} linked artifact(s).",
                    requirement="At least one artifact expected",
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Check: Integrity (SHA-256 checksums)
    # ------------------------------------------------------------------

    def _check_integrity(self, dossier: Dict[str, Any]) -> List[AuditFinding]:
        findings: List[AuditFinding] = []

        artifacts = dossier.get("artifacts") or []
        real_artifacts = [a for a in artifacts if a.get("id")]

        if not real_artifacts:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.INTEGRITY,
                    severity=AuditSeverity.WARNING,
                    message="No artifacts to verify checksums against.",
                    requirement="Artifact integrity verification",
                )
            )
            return findings

        missing_checksum = 0
        valid_checksum = 0
        for art in real_artifacts:
            checksum = art.get("checksum")
            if not checksum:
                missing_checksum += 1
            else:
                # Validate SHA-256 hex format (actual file content not in graph)
                if len(checksum) == 64 and all(
                    c in "0123456789abcdef" for c in checksum.lower()
                ):
                    valid_checksum += 1
                else:
                    findings.append(
                        AuditFinding(
                            id=str(uuid.uuid4()),
                            category=AuditCategory.INTEGRITY,
                            severity=AuditSeverity.WARNING,
                            message=(
                                f"Artifact '{art.get('id')}' has invalid checksum "
                                f"format (expected SHA-256 hex)."
                            ),
                            requirement="Artifact checksum must be valid SHA-256",
                        )
                    )

        if missing_checksum:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.INTEGRITY,
                    severity=AuditSeverity.WARNING,
                    message=f"{missing_checksum} artifact(s) have no checksum recorded.",
                    requirement="All artifacts should have SHA-256 checksums",
                )
            )

        if valid_checksum:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.INTEGRITY,
                    severity=AuditSeverity.PASS,
                    message=f"{valid_checksum} artifact(s) have valid SHA-256 checksums.",
                    requirement="Artifact checksum must be valid SHA-256",
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Check: Traceability (MOSSEC chain depth <= 7)
    # ------------------------------------------------------------------

    def _check_traceability(self, dossier_id: str) -> List[AuditFinding]:
        """Walk MOSSEC relationships from the dossier up to depth 7."""
        findings: List[AuditFinding] = []

        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})
        OPTIONAL MATCH (d)-[:CONTAINS_ARTIFACT]->(a:SimulationArtifact)
        OPTIONAL MATCH (a)-[:LINKED_TO_REQUIREMENT]->(r:Requirement)
        WITH d,
             COUNT(DISTINCT a) AS artifact_count,
             COUNT(DISTINCT r) AS linked_req_count,
             COLLECT(DISTINCT a.id) AS artifact_ids,
             COLLECT(DISTINCT r.id) AS requirement_ids
        RETURN {
            artifact_count: artifact_count,
            linked_req_count: linked_req_count,
            artifact_ids: artifact_ids,
            requirement_ids: requirement_ids
        } AS trace
        """
        rows = self._pool.execute_read(query, {"dossier_id": dossier_id})
        if not rows:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.TRACEABILITY,
                    severity=AuditSeverity.CRITICAL,
                    message="Could not fetch traceability data for dossier.",
                    requirement="MOSSEC traceability chain required",
                )
            )
            return findings

        trace = rows[0]["trace"]
        art_count = trace.get("artifact_count", 0)
        req_count = trace.get("linked_req_count", 0)

        if art_count == 0:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.TRACEABILITY,
                    severity=AuditSeverity.CRITICAL,
                    message="Dossier has no artifacts — traceability chain is broken.",
                    requirement="MOSSEC traceability chain required",
                )
            )
        elif req_count == 0:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.TRACEABILITY,
                    severity=AuditSeverity.WARNING,
                    message=(
                        f"Dossier has {art_count} artifact(s) but none link "
                        f"to a Requirement."
                    ),
                    requirement="Artifacts should trace to requirements",
                )
            )
        else:
            findings.append(
                AuditFinding(
                    id=str(uuid.uuid4()),
                    category=AuditCategory.TRACEABILITY,
                    severity=AuditSeverity.PASS,
                    message=(
                        f"Traceability chain intact: {art_count} artifact(s) -> "
                        f"{req_count} requirement(s)."
                    ),
                    requirement="MOSSEC traceability chain required",
                )
            )

        # Deep chain check (variable-length path up to depth 7)
        deep_query = """
        MATCH (d:SimulationDossier {id: $dossier_id})
        OPTIONAL MATCH path = (d)-[*1..7]-(end)
        WHERE end:Requirement OR end:SimulationRun OR end:ApprovalRecord
        WITH COUNT(DISTINCT end) AS reachable_nodes,
             COUNT(DISTINCT path) AS total_paths
        RETURN {reachable_nodes: reachable_nodes, total_paths: total_paths} AS deep
        """
        deep_rows = self._pool.execute_read(deep_query, {"dossier_id": dossier_id})
        if deep_rows:
            deep = deep_rows[0]["deep"]
            reachable = deep.get("reachable_nodes", 0)
            paths = deep.get("total_paths", 0)
            if reachable > 0:
                findings.append(
                    AuditFinding(
                        id=str(uuid.uuid4()),
                        category=AuditCategory.TRACEABILITY,
                        severity=AuditSeverity.PASS,
                        message=(
                            f"Deep trace (depth <= 7): {reachable} reachable "
                            f"governance node(s) across {paths} path(s)."
                        ),
                        requirement="MOSSEC depth-7 trace completeness",
                    )
                )

        return findings

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize(findings: List[AuditFinding]) -> AuditSummary:
        critical = sum(1 for f in findings if f.severity == AuditSeverity.CRITICAL)
        warnings = sum(1 for f in findings if f.severity == AuditSeverity.WARNING)
        passed = sum(1 for f in findings if f.severity == AuditSeverity.PASS)
        return AuditSummary(critical=critical, warnings=warnings, passed=passed)

    @staticmethod
    def _compute_score(summary: AuditSummary) -> float:
        """Compute a 0-100 health score.

        Formula:
          - Start at 100
          - Each critical finding deducts 20 points
          - Each warning deducts 5 points
          - Floor at 0
        """
        score = 100.0 - (summary.critical * 20) - (summary.warnings * 5)
        return max(0.0, round(score, 1))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_findings(
        self, dossier_id: str, findings: List[AuditFinding]
    ) -> None:
        """Write ``AuditFinding`` nodes linked to the dossier via ``[:HAS_FINDING]``."""
        if not findings:
            return

        query = """
        MATCH (d:SimulationDossier {id: $dossier_id})
        UNWIND $findings AS f
        MERGE (af:AuditFinding {id: f.id})
        SET af.category    = f.category,
            af.severity    = f.severity,
            af.message     = f.message,
            af.requirement = f.requirement,
            af.created_at  = datetime()
        MERGE (d)-[:HAS_FINDING]->(af)
        """
        finding_dicts = [
            {
                "id": f.id,
                "category": f.category.value,
                "severity": f.severity.value,
                "message": f.message,
                "requirement": f.requirement,
            }
            for f in findings
        ]
        try:
            self._pool.execute_write(query, {
                "dossier_id": dossier_id,
                "findings": finding_dicts,
            })
        except Exception as exc:
            logger.error(f"Failed to persist audit findings for {dossier_id}: {exc}")
