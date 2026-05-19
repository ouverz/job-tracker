import json
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
from ..database import db
from ..schemas import ScrapingRun, ScrapingRunDetail
from ..scrapers.runner import start_pipeline_thread, SOURCE_LABELS
from ..constants import SSE_POLL_INTERVAL_SEC, SSE_TIMEOUT_POLLS

router = APIRouter(prefix="/api/scraping", tags=["scraping"])


def _row_to_run(row, details=None) -> dict:
    d = dict(row)
    d["details"] = details or []
    return d


def _get_run_with_details(run_id: int) -> Optional[dict]:
    with db() as conn:
        run = conn.execute(
            "SELECT * FROM scraping_runs WHERE id = ?", (run_id,)
        ).fetchone()
        if not run:
            return None
        details = conn.execute(
            "SELECT * FROM scraping_run_details WHERE run_id = ? ORDER BY id",
            (run_id,),
        ).fetchall()
    return _row_to_run(run, [dict(d) for d in details])


@router.post("/run")
def trigger_run(sources: Optional[list[str]] = None):
    with db() as conn:
        cursor = conn.execute("INSERT INTO scraping_runs (status) VALUES ('running')")
        run_id = cursor.lastrowid

    start_pipeline_thread(run_id, sources)
    return {"run_id": run_id}


@router.get("/runs")
def list_runs(limit: int = 20):
    with db() as conn:
        runs = conn.execute(
            "SELECT * FROM scraping_runs ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in runs]


@router.get("/runs/latest")
def get_latest_run():
    with db() as conn:
        run = conn.execute(
            "SELECT * FROM scraping_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        if not run:
            return None
        details = conn.execute(
            "SELECT * FROM scraping_run_details WHERE run_id = ? ORDER BY id",
            (run["id"],),
        ).fetchall()
    return _row_to_run(run, [dict(d) for d in details])


@router.get("/runs/{run_id}")
def get_run(run_id: int):
    result = _get_run_with_details(run_id)
    if not result:
        raise HTTPException(404, "Run not found")
    return result


@router.get("/runs/{run_id}/stream")
def stream_run(run_id: int):
    """Server-Sent Events stream for live scraping progress."""

    def event_generator():
        # seen_states tracks a "signature" string for each source and the run itself.
        # We only emit an SSE event when the signature changes — this prevents sending
        # redundant events on every poll when nothing has actually updated.
        seen_states: dict[str, str] = {}

        for _ in range(SSE_TIMEOUT_POLLS):
            with db() as conn:
                run = conn.execute(
                    "SELECT * FROM scraping_runs WHERE id = ?", (run_id,)
                ).fetchone()
                if not run:
                    yield 'event: error\ndata: {"error": "Run not found"}\n\n'
                    return

                details = conn.execute(
                    "SELECT * FROM scraping_run_details WHERE run_id = ? ORDER BY id",
                    (run_id,),
                ).fetchall()

            # Emit updates for changed sources
            for detail in details:
                key = detail["source"]
                state_sig = (
                    f"{detail['status']}:{detail['jobs_found']}:{detail['jobs_new']}"
                )
                if seen_states.get(key) != state_sig:
                    seen_states[key] = state_sig
                    data = json.dumps(dict(detail))
                    yield f"event: source_update\ndata: {data}\n\n"

            # Emit run status
            run_sig = f"{run['status']}:{run['finished_at']}"
            if seen_states.get("__run__") != run_sig:
                seen_states["__run__"] = run_sig
                run_data = json.dumps(dict(run))
                yield f"event: run_update\ndata: {run_data}\n\n"

            if run["status"] in ("completed", "failed"):
                yield "event: done\ndata: {}\n\n"
                return

            time.sleep(SSE_POLL_INTERVAL_SEC)

        yield "event: timeout\ndata: {}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
