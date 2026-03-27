from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel
from ..database import db
from ..schemas import Job, JobSummary, JobUpdate, JobsResponse, StatsResponse
from ..constants import DEFAULT_PAGE_SIZE

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

VALID_STATUSES = {"new", "applied", "rejected", "pending", "archived", "interview"}
VALID_SORTS = {"scraped_at", "cv_score", "posted_at", "created_at", "title"}
ALLOWED_UPDATE_FIELDS = {"status", "notes", "applied_at", "starred", "follow_up_at"}


def _row_to_summary(row) -> dict:
    return {
        "id": row["id"],
        "source": row["source"],
        "url": row["url"],
        "title": row["title"],
        "company": row["company"],
        "location": row["location"],
        "employment_type": row["employment_type"],
        "remote_type": row["remote_type"],
        "salary_raw": row["salary_raw"],
        "posted_at": row["posted_at"],
        "scraped_at": row["scraped_at"],
        "status": row["status"],
        "cv_score": row["cv_score"],
        "cv_scored_at": row["cv_scored_at"],
        "starred": row["starred"] if row["starred"] is not None else 0,
        "follow_up_at": row["follow_up_at"],
        "has_description": bool(row["has_description"]),
        "cv_score_rationale": row["cv_score_rationale"],
        "cv_score_breakdown": row["cv_score_breakdown"],
    }


@router.get("", response_model=JobsResponse)
def list_jobs(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    remote_type: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    scraped_days: Optional[int] = Query(None, ge=1, le=365),
    q: Optional[str] = Query(None),
    starred: Optional[bool] = Query(None),
    exclude_starred: bool = Query(False),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    max_score: Optional[int] = Query(None, ge=0, le=100),
    no_jd: Optional[bool] = Query(None),
    sort: str = Query("scraped_at"),
    order: str = Query("desc"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    if sort not in VALID_SORTS:
        sort = "scraped_at"
    order_sql = "DESC" if order.lower() == "desc" else "ASC"

    # Each active filter appends a SQL fragment and its bound parameters to
    # these lists; they're joined into a single WHERE clause at the end.
    # This avoids a proliferation of if/elif branches for every combination.
    conditions = []
    params = []

    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip() in VALID_STATUSES]
        if statuses:
            placeholders = ",".join("?" * len(statuses))
            conditions.append(f"status IN ({placeholders})")
            params.extend(statuses)

    if source:
        sources = [s.strip() for s in source.split(",")]
        if sources:
            placeholders = ",".join("?" * len(sources))
            conditions.append(f"source IN ({placeholders})")
            params.extend(sources)

    if employment_type:
        conditions.append("employment_type = ?")
        params.append(employment_type)

    if remote_type:
        conditions.append("remote_type = ?")
        params.append(remote_type)

    if location:
        conditions.append("location LIKE ?")
        params.append(f"%{location}%")

    if scraped_days:
        cutoff = (datetime.utcnow() - timedelta(days=scraped_days)).isoformat()
        conditions.append("scraped_at >= ?")
        params.append(cutoff)

    if q:
        conditions.append("(title LIKE ? OR company LIKE ? OR description LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like])

    if starred is not None:
        conditions.append("starred = ?")
        params.append(1 if starred else 0)

    if exclude_starred:
        conditions.append("(starred = 0 OR starred IS NULL)")

    if min_score is not None:
        conditions.append("cv_score >= ?")
        params.append(min_score)

    if max_score is not None:
        conditions.append("cv_score <= ?")
        params.append(max_score)

    if no_jd:
        conditions.append("(description IS NULL OR description = '')")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    sort_expr = f"CASE WHEN {sort} IS NULL THEN 1 ELSE 0 END, {sort} {order_sql}"

    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM jobs {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, source, url, title, company, location, employment_type, remote_type, "
            f"salary_raw, posted_at, scraped_at, status, cv_score, cv_scored_at, cv_score_rationale, cv_score_breakdown, starred, follow_up_at, "
            f"CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END as has_description "
            f"FROM jobs {where} ORDER BY {sort_expr} LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    return {"items": [_row_to_summary(r) for r in rows], "total": total}


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    with db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        by_status = {r[0]: r[1] for r in conn.execute(
            "SELECT status, COUNT(*) FROM jobs GROUP BY status"
        ).fetchall()}
        by_source = {r[0]: r[1] for r in conn.execute(
            "SELECT source, COUNT(*) FROM jobs GROUP BY source"
        ).fetchall()}
        unscored = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE cv_score IS NULL AND description IS NOT NULL"
        ).fetchone()[0]

    return {"total": total, "by_status": by_status, "by_source": by_source, "unscored": unscored}


@router.get("/kpi")
def get_kpi():
    cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
    today = datetime.utcnow().date().isoformat()
    week_start = (datetime.utcnow() - timedelta(days=7)).isoformat()

    with db() as conn:
        applied_daily = [
            {"date": r[0], "count": r[1]}
            for r in conn.execute(
                "SELECT DATE(applied_at), COUNT(*) FROM jobs "
                "WHERE applied_at IS NOT NULL AND applied_at >= ? "
                "GROUP BY DATE(applied_at) ORDER BY 1",
                (cutoff,),
            ).fetchall()
        ]
        rejections_daily = [
            {"date": r[0], "count": r[1]}
            for r in conn.execute(
                "SELECT DATE(status_changed_at), COUNT(*) FROM jobs "
                "WHERE status = 'rejected' AND status_changed_at IS NOT NULL AND status_changed_at >= ? "
                "GROUP BY DATE(status_changed_at) ORDER BY 1",
                (cutoff,),
            ).fetchall()
        ]
        by_status = {r[0]: r[1] for r in conn.execute(
            "SELECT status, COUNT(*) FROM jobs GROUP BY status"
        ).fetchall()}
        applied_today = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE DATE(applied_at) = ?", (today,)
        ).fetchone()[0]
        applied_this_week = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE applied_at >= ?", (week_start,)
        ).fetchone()[0]
        total_all = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        with_jd = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE description IS NOT NULL AND description != ''"
        ).fetchone()[0]

    jd_pct = round(with_jd / total_all * 100) if total_all > 0 else 0

    return {
        "applied_daily": applied_daily,
        "rejections_daily": rejections_daily,
        "summary": {
            "total_applied": by_status.get("applied", 0),
            "total_rejected": by_status.get("rejected", 0),
            "total_interview": by_status.get("interview", 0),
            "pending": by_status.get("pending", 0),
            "applied_today": applied_today,
            "applied_this_week": applied_this_week,
            "jd_coverage_pct": jd_pct,
            "with_jd": with_jd,
            "total_jobs": total_all,
        },
    }


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Job not found")
    return dict(row)


@router.patch("/{job_id}", response_model=Job)
def update_job(job_id: int, update: JobUpdate):
    fields = {k: v for k, v in update.model_dump().items() if v is not None and k in ALLOWED_UPDATE_FIELDS}
    if not fields:
        raise HTTPException(400, "No fields to update")

    if "status" in fields and fields["status"] not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: {fields['status']}")

    now = datetime.utcnow().isoformat()
    fields["updated_at"] = now
    if "status" in fields:
        fields["status_changed_at"] = now
        if fields["status"] == "applied" and "applied_at" not in fields:
            # Auto-set applied_at if not explicitly provided
            with db() as conn:
                existing = conn.execute("SELECT applied_at FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if existing and not existing["applied_at"]:
                fields["applied_at"] = now

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    params = list(fields.values()) + [job_id]

    with db() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    if not row:
        raise HTTPException(404, "Job not found")
    return dict(row)


class BatchStatusUpdate(BaseModel):
    job_ids: list[int]
    status: str


@router.patch("/batch-status", response_model=dict)
def batch_update_status(update: BatchStatusUpdate):
    if update.status not in VALID_STATUSES:
        raise HTTPException(400, f"Invalid status: {update.status}")
    if not update.job_ids:
        raise HTTPException(400, "No job IDs provided")

    now = datetime.utcnow().isoformat()
    placeholders = ",".join("?" * len(update.job_ids))
    with db() as conn:
        conn.execute(
            f"UPDATE jobs SET status = ?, status_changed_at = ?, updated_at = ? WHERE id IN ({placeholders})",
            [update.status, now, now] + update.job_ids,
        )
    return {"updated": len(update.job_ids)}


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: int):
    with db() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
