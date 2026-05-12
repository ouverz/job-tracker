# backend/app/services/

Business logic layer called by the API routers.

## Files

### `scoring.py`
CV-to-JD ATS scoring via the Anthropic API (tool_use for structured output).

**Key exports:**
- `score_job(job_id)` — scores a single job, writes result to DB, returns score dict
- `start_batch_score(job_ids?)` — runs scoring in a background thread for multiple jobs; uses `ThreadPoolExecutor` with `BATCH_SCORE_WORKERS=3` concurrent threads
- `get_batch_status()` — returns current batch progress state

**Concurrency:**
Batch scoring runs `BATCH_SCORE_WORKERS` (default 3) jobs in parallel via `ThreadPoolExecutor`. Each thread gets its own SQLite connection (`db()` creates a new connection per call) and updates only its own row, so there is no contention. The shared `_batch_state` counter is protected by `_state_lock` (a `threading.Lock`).

**Scoring prompt:**
The system prompt encodes the candidate's hard constraints directly so Claude can apply them without inferring from CV text:
- Location: Frankfurt am Main area, max 45 min by train. On-site/hybrid roles in Munich, Hamburg, Berlin, Stuttgart, or Cologne are penalised via `location_score`.
- Language: English C2, German B1. Roles requiring German B2+ are hard-blocked: `overall_score` capped at 45, `language_match_score` ≤ 20.
- Tools: Required tools missing from CV must be listed in `gaps[]` explicitly.

**Breakdown fields stored in `cv_score_breakdown` (JSON blob):**

| Field | Type | Description |
|-------|------|-------------|
| `skill_match_score` | 0–100 | Technical skills coverage |
| `experience_match_score` | 0–100 | Experience level alignment |
| `language_match_score` | 0–100 | Language requirements fit; 0 if German B2+ required |
| `location_score` | 0–100 | Location/commute fit; penalised for remote-unfriendly roles far from Frankfurt |
| `strengths` | string[] | Top CV strengths relevant to the role |
| `gaps` | string[] | Required JD items not covered by CV |

### `enrichment.py`
Description backfill for jobs missing JDs.

**Key exports:**
- `start_backfill(sources?, limit?, status?)` — queues a background thread to fetch missing descriptions. Supports `stepstone`, `linkedin`, and `indeed`. Pass `status="new"` to restrict to inbox jobs only. Returns number of jobs queued (0 if already running or nothing to do).
- `get_backfill_status()` — returns `{running, done, total, errors, source_counts}`.

**Per-source fetch strategy:**

| Source | Approach |
|--------|----------|
| `stepstone` | HTML — `data-at="job-ad-details"` container |
| `linkedin` | HTML — `description__text` / `show-more-less-html` class selectors |
| `indeed` | JSON-LD first (`<script type="application/ld+json">`), then `#jobDescriptionText`, then class-pattern fallback |

All fetchers use randomised polite delays (`ENRICH_SLEEP_MIN_SEC`–`ENRICH_SLEEP_MAX_SEC`) to avoid rate-limiting. Indeed and LinkedIn have anti-bot measures; expect partial success on those sources.

### `contacts.py`
Network contact management per job (lookup, add, remove).

### `enrichment.py`
Job enrichment logic (e.g. extracting structured fields from raw descriptions).

### `title_filter.py`
Heuristic filter to skip irrelevant job titles before saving to DB.
