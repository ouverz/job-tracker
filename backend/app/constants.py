"""Central module for magic constants used across the application."""

# Scoring — CV and JD text is truncated before sending to Claude.
# 8000 chars covers most CVs without wasting tokens; 5000 is enough for
# a typical JD while staying well inside a single API call's context.
CV_CHAR_LIMIT = 8000
JD_CHAR_LIMIT = 5000

# Batch scoring background thread
BATCH_POLL_SLEEP_SEC = 1.0

# SSE streaming (scraping progress feed)
SSE_POLL_INTERVAL_SEC = 1.0
SSE_TIMEOUT_POLLS = 300  # 5 minutes

# Enrichment / description backfill — random delay between HTTP requests
# to avoid rate-limiting on StepStone and LinkedIn
ENRICH_SLEEP_MIN_SEC = 2.0
ENRICH_SLEEP_MAX_SEC = 5.0

# Jobs list — default page size returned by GET /api/jobs
DEFAULT_PAGE_SIZE = 15
