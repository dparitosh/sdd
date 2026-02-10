"""STEP ingestion routes (FastAPI).

These endpoints exist so agents/tools can ingest STEP instance files into Neo4j.

Security:
- Requires API key
- Restricts file paths to known safe roots inside the repo
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, Field

from src.web.dependencies import get_api_key
from src.web.app_fastapi import Neo4jJSONResponse
from src.web.services.step_ingest_service import StepIngestConfig, StepIngestService


router = APIRouter(prefix="/api/step", tags=["STEP Ingestion"])


class StepIngestRequest(BaseModel):
    path: str = Field(..., description="Path to .stp/.step/.stpx file under allowed roots")
    label: Optional[str] = Field(None, description="Optional label/name for the file")
    batch_size: int = Field(500, ge=1, le=5000, description="Neo4j UNWIND batch size")


class StepIngestResponse(BaseModel):
    success: bool
    message: str
    stats: dict


def _repo_root() -> Path:
    # backend/src/web/routes -> backend/src/web -> backend/src -> backend -> repo
    return Path(__file__).resolve().parents[4]


def _resolve_safe_path(user_path: str) -> Path:
    root = _repo_root()
    p = Path(user_path)

    if not p.is_absolute():
        p = (root / p).resolve()
    else:
        p = p.resolve()

    allowed_roots = [
        (root / "data" / "uploads").resolve(),
        (root / "data" / "raw").resolve(),
        (root / "smrlv12").resolve(),
    ]

    def _is_under(path: Path, base: Path) -> bool:
        # Avoid prefix tricks like ".../raw2" matching ".../raw".
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False

    if not any(_is_under(p, ar) for ar in allowed_roots):
        raise HTTPException(
            status_code=400,
            detail=(
                "Path is not under an allowed root. Allowed roots: "
                + ", ".join(str(ar) for ar in allowed_roots)
            ),
        )

    if p.suffix.lower() not in {".stp", ".step", ".stpx"}:
        raise HTTPException(
            status_code=400,
            detail="Unsupported STEP extension. Use .stp/.step (Part 21) or .stpx (STEP-XML)",
        )

    if not p.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {p}")

    return p


@router.post("/ingest", response_model=StepIngestResponse, response_class=Neo4jJSONResponse)
async def ingest_step(
    req: StepIngestRequest,
    _api_key: str = Depends(get_api_key),
):
    try:
        step_path = _resolve_safe_path(req.path)

        service = StepIngestService(StepIngestConfig(batch_size=req.batch_size))
        stats = service.ingest_file(step_path, file_label=req.label)

        return {
            "success": True,
            "message": f"Ingested STEP file: {step_path.name}",
            "stats": stats.__dict__,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"STEP ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
