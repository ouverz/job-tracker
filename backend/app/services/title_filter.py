"""Title-based bulk archiving filter."""
import re
from datetime import datetime
from ..database import db

# Explicit denials — checked first, take precedence over keep patterns
DENY_PATTERNS = [
    r"\bproduct manager\b",
    r"\bsales manager\b",
    r"\bsolution sales\b",
    r"\bfrontend (engineer|developer|dev)\b",
    r"\bembedded (engineer|developer|software)\b",
    r"\brf intelligence\b",
    r"\bphd (thesis|position)\b",
    r"\bweiterbildung\b",
    r"\bvice president\b",
    r"technical design lead.{0,20}data cent",
    r"system engineer.{0,20}data cent",
]

# Relevant roles — if any match and not denied, the job is kept
KEEP_PATTERNS = [
    # Data engineering family
    r"data engineer",
    r"analytics engineer",
    r"data architect",
    r"datenarchitekt",
    r"data analyst",
    r"data scientist",
    r"data science (manager|lead|head)",
    r"data platform",
    r"data (& |and )?ai",
    r"data (& |and )?innovation",
    r"data strategy",
    r"data management",
    r"data curation",
    r"data visualization (engineer|developer|analyst)",
    r"data (operations|ops) engineer",
    r"data space architect",
    r"data governance.{0,20}(engineer|spezialist|architect)",
    r"data warehouse",
    r"data lake",
    r"scientific data",
    r"industrial data engineer",
    r"fleet analytics",
    r"big data",
    r"\biiot\b",
    r"\brpa\b",
    # ML/AI engineering family
    r"ml engineer",
    r"ml research",
    r"mlops",
    r"machine learning",
    r"\bdeep learning\b",
    r"\bnlp\b",
    r"\bllm\b",
    r"foundation model",
    r"reinforcement learning",
    # AI * role — catches AI Engineer, AI Architect, AI Platform Engineer,
    # AI Backend Developer, AI DevOps Engineer, AI Research Engineer, etc.
    r"\bai[-\s]?(engineer|architect|developer|platform|solution|research|devops"
    r"|application|operations|workflow|backend|governance|lead|agent|evaluation)\b",
    r"\bai/ml\b",
    r"genai",
    r"gen(erative)? ai",
    r"\bagentic.?ai\b",
    r"\bagenticai\b",
    r"\bagetnic",  # SAP typo for "agentic"
    r"\bagentic\b",
    r"conversational ai",
    r"artificial intelligence",
    r"\bki[-\s](entwickler|engineer|spezialist|lösung|plattform|fachreferent)\b",
    r"fachreferent.{0,30}\bki\b",
    # Platform / infra with data focus
    r"databricks",
    r"snowflake.{0,20}(engineer|architect|developer)",
    r"\bsap data\b",
    r"\bdatasphere\b",         # SAP Datasphere = data platform
    r"data security engineer",
    r"\bbi[-\s]?(engineer|developer)\b",
    r"business intelligence (engineer|developer)",
    r"knowledge graph",
    r"automat(ion|isierung)",
    r"forward deployed",
    # Leadership with data/AI focus
    r"\bhead of data\b",
    r"\bhead of engineering.{0,20}(ai|data)\b",
    r"\bstaff (data|ml|machine learning)\b",
    r"engineering manager.{0,20}(ai|data)",
    r"ranking.{0,20}(data|scientist)",
    r"senior expert.{0,20}artificial",
    r"(senior|staff|lead) (data|ml|ai|machine)",
    # Mixed software+data/AI roles
    r"solution architect.{0,20}(data|ai|database)",
    r"software architect.{0,20}(data|ai|analytics)",
    r"software (engineer|developer).{0,30}\bai\b",
    r"\bai\b.{0,30}software (engineer|developer)",
    r"full.?stack.{0,20}(data|ai)",
    r"(data|ai).{0,20}full.?stack",
    r"software engineer.{0,10}data",
    r"applied scientist",
    r"research engineer.{0,20}(model|foundation|ml|ai)",
    # Other relevant
    r"scientific data",
    r"\biiot\b",
]


def _compile(patterns: list[str]) -> list[re.Pattern]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


_DENY = _compile(DENY_PATTERNS)
_KEEP = _compile(KEEP_PATTERNS)


def classify_title(title: str) -> str:
    """Returns 'archive' or 'keep'."""
    # Deny is checked first so explicit exclusions (e.g. "frontend developer") take
    # precedence over broad keep patterns that might accidentally match them
    # (e.g. a "software engineer — AI/frontend" title would otherwise be kept).
    for pat in _DENY:
        if pat.search(title):
            return "archive"
    for pat in _KEEP:
        if pat.search(title):
            return "keep"
    # Default: archive anything that doesn't match a keep pattern.
    return "archive"


def get_filter_preview(status: str = "new") -> dict:
    """Dry-run: return which jobs would be archived vs kept."""
    with db() as conn:
        rows = conn.execute(
            "SELECT id, title, company, source FROM jobs WHERE status = ?",
            (status,),
        ).fetchall()

    to_archive = []
    to_keep = []
    for row in rows:
        entry = {
            "id": row["id"],
            "title": row["title"],
            "company": row["company"],
            "source": row["source"],
        }
        if classify_title(row["title"]) == "archive":
            to_archive.append(entry)
        else:
            to_keep.append(entry)

    return {
        "to_archive": to_archive,
        "to_keep": to_keep,
        "archive_count": len(to_archive),
        "keep_count": len(to_keep),
    }


def apply_title_filter(status: str = "new") -> int:
    """Archive jobs whose titles don't match keep patterns. Returns count archived."""
    preview = get_filter_preview(status)
    job_ids = [j["id"] for j in preview["to_archive"]]
    if not job_ids:
        return 0

    now = datetime.utcnow().isoformat()
    placeholders = ",".join("?" * len(job_ids))
    with db() as conn:
        conn.execute(
            f"UPDATE jobs SET status = 'archived', status_changed_at = ?, updated_at = ?"
            f" WHERE id IN ({placeholders})",
            [now, now] + job_ids,
        )
    return len(job_ids)
