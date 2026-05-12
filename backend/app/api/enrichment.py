"""Enrichment API: title filtering and description backfill."""
from fastapi import APIRouter, Query
from typing import Optional

from ..services.title_filter import get_filter_preview, apply_title_filter
from ..services.enrichment import start_backfill, get_backfill_status

router = APIRouter(prefix="/api/enrichment", tags=["enrichment"])


@router.get("/title-filter-preview")
def title_filter_preview(status: str = Query("new")):
    """Dry-run: returns which jobs would be archived vs kept by the title filter."""
    return get_filter_preview(status)


@router.post("/title-filter-apply")
def title_filter_apply(status: str = Query("new")):
    """Apply title filter and archive irrelevant jobs."""
    archived = apply_title_filter(status)
    return {"archived": archived}


@router.post("/backfill-descriptions")
def backfill_descriptions(
    sources: Optional[str] = Query(None, description="Comma-separated sources: stepstone,linkedin,indeed"),
    limit: int = Query(300, ge=1, le=500),
    status: Optional[str] = Query(None, description="Restrict to jobs with this status, e.g. 'new'"),
):
    """Start background task to fetch missing job descriptions."""
    source_list = [s.strip() for s in sources.split(",")] if sources else None
    queued = start_backfill(sources=source_list, limit=limit, status=status)
    if queued == 0:
        current = get_backfill_status()
        if current["running"]:
            return {"queued": 0, "message": "Backfill already running", "status": current}
        return {"queued": 0, "message": "Nothing to backfill"}
    return {"queued": queued, "message": f"Backfill started for {queued} jobs"}


@router.get("/backfill-status")
def backfill_status():
    """Get progress of the current/last backfill run."""
    return get_backfill_status()
