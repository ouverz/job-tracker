"""CV-to-JD ATS scoring using Anthropic API."""

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from ..config import settings
from ..database import db
from ..constants import CV_CHAR_LIMIT, JD_CHAR_LIMIT, BATCH_SCORE_WORKERS
from datetime import datetime

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


SCORE_TOOL = {
    "name": "submit_job_score",
    "description": "Submit your compatibility analysis between the candidate CV and job description",
    "input_schema": {
        "type": "object",
        "properties": {
            "overall_score": {
                "type": "integer",
                "description": "Overall compatibility score 0-100",
                "minimum": 0,
                "maximum": 100,
            },
            "skill_match_score": {
                "type": "integer",
                "description": "Technical skills match score 0-100",
                "minimum": 0,
                "maximum": 100,
            },
            "experience_match_score": {
                "type": "integer",
                "description": "Experience level match score 0-100",
                "minimum": 0,
                "maximum": 100,
            },
            "language_match_score": {
                "type": "integer",
                "description": "Language requirements fit 0-100. 0 if the job requires a language level the candidate cannot meet.",
                "minimum": 0,
                "maximum": 100,
            },
            "location_score": {
                "type": "integer",
                "description": "Location fit 0-100. Score heavily penalized if on-site/hybrid and the office is beyond the candidate's acceptable commute distance.",
                "minimum": 0,
                "maximum": 100,
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top 3-5 CV strengths most relevant to this role",
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key requirements in JD not covered by CV",
            },
            "summary": {
                "type": "string",
                "description": "2-3 sentence plain English rationale for the score",
            },
        },
        "required": [
            "overall_score",
            "skill_match_score",
            "experience_match_score",
            "language_match_score",
            "location_score",
            "strengths",
            "gaps",
            "summary",
        ],
    },
}


def _build_system_prompt() -> str:
    """Build the scoring system prompt from candidate settings in .env."""
    loc = settings.candidate_location
    commute = settings.candidate_max_commute_min
    lang = settings.candidate_language_requirement
    return f"""You are an expert ATS system evaluating job-CV compatibility.

Candidate profile:
- Location: {loc} — max acceptable commute is {commute} minutes by train.
  Penalise heavily if the role is on-site or hybrid AND the office city is likely
  more than {commute} minutes by train from {loc}.
- Language: English C2 (native/mastery), {lang}.
  If the job *requires* a language level the candidate cannot meet — treat this as a hard
  blocker: cap overall_score at 45 and set language_match_score <= 20.
  If the job *prefers* (not requires) a higher level — deduct 10-15 points from language_match_score.
- Tools: Any tool listed as *required* in the JD that does not appear in the CV is a significant
  gap. Do not ignore it or treat it as minor. List it explicitly in gaps[].

Scoring thresholds: 80+ strong match, 50-79 partial match, below 50 weak match.
Be calibrated — most roles should not score 80+."""


def _build_prompt(
    cv_text: str, job_title: str, job_company: Optional[str], jd_text: str
) -> str:
    # CV and JD are truncated to stay within a reasonable token budget.
    # CV_CHAR_LIMIT covers most full CVs; JD_CHAR_LIMIT captures the
    # essential requirements without including boilerplate footer text.
    company_str = f" at {job_company}" if job_company else ""
    return f"""## Candidate CV

{cv_text[:CV_CHAR_LIMIT]}

---

## Job: {job_title}{company_str}

{jd_text[:JD_CHAR_LIMIT]}

Analyze the compatibility and call submit_job_score with your assessment."""


def score_job(job_id: int) -> dict:
    """Score a single job. Returns score dict or raises."""
    if not ANTHROPIC_AVAILABLE:
        raise RuntimeError("anthropic package not installed")
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in .env")

    cv_text = settings.get_cv_text()
    if not cv_text:
        raise RuntimeError("CV not found. Place your CV as cv.txt in the project root.")

    with db() as conn:
        row = conn.execute(
            "SELECT id, title, company, description FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()

    if not row:
        raise ValueError(f"Job {job_id} not found")

    jd_text = row["description"] or ""
    if not jd_text:
        raise ValueError("Job has no description to score against")

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_build_system_prompt(),
        tools=[SCORE_TOOL],
        tool_choice={"type": "tool", "name": "submit_job_score"},
        messages=[
            {
                "role": "user",
                "content": _build_prompt(
                    cv_text, row["title"], row["company"], jd_text
                ),
            }
        ],
    )

    # Extract tool use result
    result = None
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_job_score":
            result = block.input
            break

    if not result:
        raise RuntimeError("No score returned from Claude")

    breakdown = json.dumps(
        {
            "skill_match_score": result.get("skill_match_score"),
            "experience_match_score": result.get("experience_match_score"),
            "language_match_score": result.get("language_match_score"),
            "location_score": result.get("location_score"),
            "strengths": result.get("strengths", []),
            "gaps": result.get("gaps", []),
        }
    )

    now = datetime.utcnow().isoformat()
    with db() as conn:
        conn.execute(
            """UPDATE jobs SET cv_score = ?, cv_score_rationale = ?, cv_score_breakdown = ?,
               cv_scored_at = ?, updated_at = ? WHERE id = ?""",
            (
                result["overall_score"],
                result.get("summary", ""),
                breakdown,
                now,
                now,
                job_id,
            ),
        )

    return {
        "cv_score": result["overall_score"],
        "cv_score_rationale": result.get("summary", ""),
        "cv_score_breakdown": breakdown,
        "strengths": result.get("strengths", []),
        "gaps": result.get("gaps", []),
    }


_batch_state = {
    "running": False,
    "total": 0,
    "done": 0,
    "errors": 0,
}
_state_lock = threading.Lock()


def _score_one(job_id: int) -> None:
    for attempt in range(5):
        try:
            score_job(job_id)
            with _state_lock:
                _batch_state["done"] += 1
            return
        except Exception as e:
            is_rate_limit = "429" in str(e) or "rate_limit" in str(e)
            if is_rate_limit and attempt < 4:
                wait = 60 * (attempt + 1)
                print(
                    f"[scoring] Rate limited on job {job_id}, retrying in {wait}s (attempt {attempt + 1}/5)"
                )
                time.sleep(wait)
            else:
                print(f"[scoring] Error scoring job {job_id}: {e}")
                with _state_lock:
                    _batch_state["errors"] += 1
                return


def get_batch_status() -> dict:
    return dict(_batch_state)


def _batch_score_worker(job_ids: list[int]):
    _batch_state["running"] = True
    _batch_state["total"] = len(job_ids)
    _batch_state["done"] = 0
    _batch_state["errors"] = 0
    try:
        with ThreadPoolExecutor(max_workers=BATCH_SCORE_WORKERS) as pool:
            for _ in as_completed([pool.submit(_score_one, jid) for jid in job_ids]):
                pass  # progress tracked inside _score_one under _state_lock
    finally:
        _batch_state["running"] = False


def start_batch_score(job_ids: Optional[list[int]] = None) -> int:
    """Score multiple jobs in a background thread. Returns count queued, 0 if already running."""
    if _batch_state["running"]:
        return 0

    if job_ids is None:
        with db() as conn:
            rows = conn.execute(
                "SELECT id FROM jobs WHERE cv_score IS NULL AND description IS NOT NULL AND status != 'archived'"
            ).fetchall()
        job_ids = [r["id"] for r in rows]

    if not job_ids:
        return 0

    t = threading.Thread(target=_batch_score_worker, args=(job_ids,), daemon=True)
    t.start()
    return len(job_ids)
