from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import date, timedelta
from pydantic import BaseModel
from ..database import db

router = APIRouter(prefix="/api/activity-log", tags=["activity-log"])

# (key, label, auto_tracked, default_target)
ACTIVITIES = [
    ("applications_sent",            "Applications sent",            True,  5),
    ("outreach_sequences",           "Outreach sequences started",   False, 5),
    ("hiring_manager_conversations", "Hiring manager conversations", False, 0),
    ("linkedin_posts",               "LinkedIn posts published",     False, 1),
    ("first_round_interviews",       "First-round interviews",       False, 0),
    ("second_round_processes",       "Second-round processes",       False, 0),
    ("network_reconnects",           "Network reconnects sent",      True,  5),
    ("github_commits",               "GitHub commits",               False, 3),
]

_DEFAULT_TARGETS = {key: tgt for key, _, _, tgt in ACTIVITIES}
_VALID_KEYS = {key for key, *_ in ACTIVITIES}


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _current_week_start() -> str:
    return _monday(date.today()).isoformat()


class ActivityUpdate(BaseModel):
    actual: Optional[int] = None
    target: Optional[int] = None


@router.get("")
def get_activity_log(week: Optional[str] = Query(None)):
    week_start = _monday(date.fromisoformat(week) if week else date.today()).isoformat()
    next_monday = (date.fromisoformat(week_start) + timedelta(days=7)).isoformat()
    week_end = (date.fromisoformat(next_monday) - timedelta(days=1)).isoformat()

    with db() as conn:
        rows = conn.execute(
            "SELECT activity, actual, target FROM weekly_log WHERE week_start = ?",
            (week_start,),
        ).fetchall()
        stored = {r["activity"]: dict(r) for r in rows}

        apps = conn.execute(
            "SELECT COUNT(*) AS cnt FROM jobs WHERE status = 'applied' AND applied_at >= ? AND applied_at < ?",
            (week_start, next_monday),
        ).fetchone()["cnt"]

        reconnects = conn.execute(
            "SELECT COUNT(*) AS cnt FROM contacts WHERE reached_out = 1 AND reached_out_at >= ? AND reached_out_at < ?",
            (week_start, next_monday),
        ).fetchone()["cnt"]

    auto_actuals = {"applications_sent": apps, "network_reconnects": reconnects}

    activities = []
    for key, label, auto_tracked, default_target in ACTIVITIES:
        s = stored.get(key, {})
        target = s.get("target", default_target)
        actual = auto_actuals[key] if auto_tracked else s.get("actual", 0)

        if target == 0:
            status = "n/a"
        elif actual >= target:
            status = "on_track"
        else:
            status = "behind"

        activities.append({
            "key": key,
            "label": label,
            "auto_tracked": auto_tracked,
            "actual": actual,
            "target": target,
            "status": status,
        })

    return {"week_start": week_start, "week_end": week_end, "activities": activities}


@router.patch("/{week_start}/{activity}")
def update_activity(week_start: str, activity: str, body: ActivityUpdate):
    if activity not in _VALID_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown activity: {activity}")

    week_start = _monday(date.fromisoformat(week_start)).isoformat()

    with db() as conn:
        existing = conn.execute(
            "SELECT actual, target FROM weekly_log WHERE week_start = ? AND activity = ?",
            (week_start, activity),
        ).fetchone()

        if existing:
            new_actual = body.actual if body.actual is not None else existing["actual"]
            new_target = body.target if body.target is not None else existing["target"]
            conn.execute(
                "UPDATE weekly_log SET actual = ?, target = ? WHERE week_start = ? AND activity = ?",
                (new_actual, new_target, week_start, activity),
            )
        else:
            new_actual = body.actual if body.actual is not None else 0
            new_target = body.target if body.target is not None else _DEFAULT_TARGETS[activity]
            conn.execute(
                "INSERT INTO weekly_log (week_start, activity, actual, target) VALUES (?, ?, ?, ?)",
                (week_start, activity, new_actual, new_target),
            )

    return {"ok": True}
