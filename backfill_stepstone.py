"""Standalone script to backfill Stepstone job descriptions."""
import sys, re, time, random
sys.path.insert(0, "backend")

import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from app.database import db

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

with db() as conn:
    rows = conn.execute(
        "SELECT id, url FROM jobs WHERE (description IS NULL OR description='') "
        "AND source='stepstone' AND status != 'archived' ORDER BY id"
    ).fetchall()

print(f"Fetching descriptions for {len(rows)} Stepstone jobs...")
done = 0
errors = 0

with httpx.Client(timeout=20, follow_redirects=True) as client:
    for row in rows:
        try:
            time.sleep(random.uniform(1.5, 3.0))
            resp = client.get(row["url"], headers=HEADERS, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                el = soup.find("div", {"data-at": "job-ad-details"}) or soup.find(
                    "div", class_=re.compile(r"job-ad-display|JobAd|jobDescription", re.I)
                )
                if el:
                    desc = el.get_text(separator="\n", strip=True)
                    now = datetime.utcnow().isoformat()
                    with db() as conn:
                        conn.execute(
                            "UPDATE jobs SET description=?, updated_at=? WHERE id=?",
                            (desc, now, row["id"]),
                        )
                    done += 1
                else:
                    errors += 1
            else:
                print(f"  HTTP {resp.status_code} for job {row['id']}")
                errors += 1
        except Exception as e:
            print(f"  Error on job {row['id']}: {e}")
            errors += 1

        total = done + errors
        if total % 10 == 0:
            print(f"  {total}/{len(rows)} — {done} fetched, {errors} failed")

print(f"\nDone: {done} descriptions fetched, {errors} failed")
