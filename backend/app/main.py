from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .database import init_db, db
from .api import jobs, scraping, scoring, enrichment, cv, contacts, analysis, activity_log
from .scrapers.runner import start_pipeline_thread

app = FastAPI(title="Job Tracker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
    allow_origin_regex=r"http://(192\.168\.\d+\.\d+|100\.\d+\.\d+\.\d+)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

scheduler = AsyncIOScheduler()


def _scheduled_pipeline():
    """Called by APScheduler — creates a run record and fires the background thread."""
    try:
        with db() as conn:
            cursor = conn.execute("INSERT INTO scraping_runs (status) VALUES ('running')")
            run_id = cursor.lastrowid
        start_pipeline_thread(run_id, sources=None)
        print(f"✓ Scheduled pipeline started (run_id={run_id})")
    except Exception as e:
        print(f"✗ Scheduled pipeline failed to start: {e}")


def _archive_stale_new_jobs():
    """Archive 'new' jobs that have been sitting unseen for 14+ days."""
    from datetime import datetime, timedelta
    cutoff = (datetime.utcnow() - timedelta(days=14)).isoformat()
    now = datetime.utcnow().isoformat()
    try:
        with db() as conn:
            result = conn.execute(
                "UPDATE jobs SET status = 'archived', status_changed_at = ?, updated_at = ? "
                "WHERE status = 'new' AND scraped_at < ?",
                (now, now, cutoff),
            )
        print(f"✓ Auto-archived {result.rowcount} stale new jobs (older than 14 days)")
    except Exception as e:
        print(f"✗ Auto-archive failed: {e}")


@app.on_event("startup")
def startup():
    init_db()
    print("✓ Database initialised")
    scheduler.add_job(_scheduled_pipeline, "cron", hour=8, minute=0, id="daily_pipeline", replace_existing=True)
    scheduler.add_job(_archive_stale_new_jobs, "cron", hour=9, minute=0, id="daily_archive_stale", replace_existing=True)
    scheduler.start()
    print("✓ Scheduler started (daily pipeline at 08:00, stale-job archive at 09:00)")


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown(wait=False)


# Routers
app.include_router(jobs.router)
app.include_router(scraping.router)
app.include_router(scoring.router)
app.include_router(enrichment.router)
app.include_router(cv.router)
app.include_router(contacts.router)
app.include_router(analysis.router)
app.include_router(activity_log.router)

# Health check
@app.get("/api/health")
def health():
    return {"status": "ok"}

# Serve built frontend (production mode)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        index = frontend_dist / "index.html"
        return FileResponse(str(index))
