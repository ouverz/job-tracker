"""Re-scrape LinkedIn with linkedin_fetch_description=True and update existing records."""
import sys
sys.path.insert(0, "backend")

from jobspy import scrape_jobs
from datetime import datetime
from app.database import db
from app.scrapers.base import SEARCH_ROLES

# Load existing LinkedIn job URLs that need descriptions
with db() as conn:
    rows = conn.execute(
        "SELECT id, url FROM jobs "
        "WHERE source='linkedin' AND status != 'archived' "
        "AND (description IS NULL OR description='')"
    ).fetchall()

existing = {row["url"]: row["id"] for row in rows}
print(f"LinkedIn jobs needing descriptions: {len(existing)}")

updated = 0
errors = 0

for role in SEARCH_ROLES:
    print(f"\nSearching: {role}")
    try:
        df = scrape_jobs(
            site_name=["linkedin"],
            search_term=role,
            location="Germany",
            results_wanted=50,
            hours_old=400,
            linkedin_fetch_description=True,
            verbose=0,
        )
        if df is None or df.empty:
            print(f"  No results")
            continue

        matched = 0
        for _, row in df.iterrows():
            url = str(row.get("job_url", "")).strip()
            desc = str(row.get("description", "") or "").strip()
            if url in existing and desc and len(desc) > 100:
                job_id = existing[url]
                now = datetime.utcnow().isoformat()
                with db() as conn:
                    conn.execute(
                        "UPDATE jobs SET description=?, updated_at=? WHERE id=?",
                        (desc, now, job_id),
                    )
                updated += 1
                matched += 1
                del existing[url]  # don't update twice

        print(f"  {len(df)} results, {matched} matched and updated")

    except Exception as e:
        print(f"  Error: {e}")
        errors += 1

print(f"\nDone: {updated} descriptions updated, {errors} search errors")
print(f"Still missing: {len(existing)}")
