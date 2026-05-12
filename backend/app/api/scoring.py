from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..schemas import ScoreResult
from ..services.scoring import score_job, start_batch_score, get_batch_status
from ..database import db

router = APIRouter(prefix="/api/scoring", tags=["scoring"])


@router.post("/jobs/{job_id}", response_model=ScoreResult)
def score_single_job(job_id: int):
    try:
        result = score_job(job_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.post("/batch")
def batch_score(
    job_ids: Optional[list[int]] = None,
    status: Optional[str] = Query(None, description="Only score jobs with this status (e.g. 'new')"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Re-score jobs with cv_score >= this value"),
    max_score: Optional[int] = Query(None, ge=0, le=100, description="Re-score jobs with cv_score <= this value"),
):
    """Score all unscored jobs (or a subset). Use status to filter by job status, min_score/max_score to re-score a score range."""
    try:
        if status is not None or min_score is not None or max_score is not None:
            conditions = ["description IS NOT NULL", "status != 'archived'", "cv_score IS NULL"]
            params = []
            if status is not None:
                conditions.append("status = ?")
                params.append(status)
            if min_score is not None:
                conditions.append("cv_score >= ?")
                params.append(min_score)
            if max_score is not None:
                conditions.append("cv_score <= ?")
                params.append(max_score)
            with db() as conn:
                rows = conn.execute(
                    f"SELECT id FROM jobs WHERE {' AND '.join(conditions)}", params
                ).fetchall()
            job_ids = [r["id"] for r in rows]

        queued = start_batch_score(job_ids)
        if queued == 0:
            status = get_batch_status()
            if status["running"]:
                return {"queued": 0, "message": "Batch already running", **status}
        return {"queued": queued, "message": f"Scoring {queued} jobs in background"}
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/batch/status")
def batch_status():
    """Get current batch scoring progress."""
    return get_batch_status()
