# backend/app/services/

Business logic layer called by the API routers.

## Files

### `scoring.py`
CV-to-JD ATS scoring via the Anthropic API (tool_use for structured output).

**Key exports:**
- `score_job(job_id)` — scores a single job, writes result to DB, returns score dict
- `start_batch_score(job_ids?)` — runs scoring in a background thread for multiple jobs
- `get_batch_status()` — returns current batch progress state

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

### `contacts.py`
Network contact management per job (lookup, add, remove).

### `enrichment.py`
Job enrichment logic (e.g. extracting structured fields from raw descriptions).

### `title_filter.py`
Heuristic filter to skip irrelevant job titles before saving to DB.
