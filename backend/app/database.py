import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

DB_PATH = os.environ.get("DB_PATH", Path(__file__).parent.parent / "data" / "jobs.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id     TEXT,
                source          TEXT NOT NULL,
                url             TEXT NOT NULL UNIQUE,
                title           TEXT NOT NULL,
                company         TEXT,
                location        TEXT,
                employment_type TEXT,
                remote_type     TEXT,
                salary_raw      TEXT,
                description     TEXT,
                posted_at       TEXT,
                scraped_at      TEXT NOT NULL DEFAULT (datetime('now')),
                status          TEXT NOT NULL DEFAULT 'new',
                notes           TEXT,
                applied_at      TEXT,
                cv_score        REAL,
                cv_score_rationale  TEXT,
                cv_score_breakdown  TEXT,
                cv_scored_at    TEXT,
                content_hash    TEXT,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_status   ON jobs(status);
            CREATE INDEX IF NOT EXISTS idx_jobs_source   ON jobs(source);
            CREATE INDEX IF NOT EXISTS idx_jobs_score    ON jobs(cv_score DESC);
            CREATE INDEX IF NOT EXISTS idx_jobs_scraped  ON jobs(scraped_at DESC);

            CREATE TABLE IF NOT EXISTS scraping_runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at  TEXT NOT NULL DEFAULT (datetime('now')),
                finished_at TEXT,
                status      TEXT NOT NULL DEFAULT 'running'
            );

            CREATE TABLE IF NOT EXISTS scraping_run_details (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id      INTEGER NOT NULL REFERENCES scraping_runs(id),
                source      TEXT NOT NULL,
                status      TEXT NOT NULL DEFAULT 'pending',
                jobs_found  INTEGER DEFAULT 0,
                jobs_new    INTEGER DEFAULT 0,
                error_msg   TEXT,
                started_at  TEXT,
                finished_at TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        # Idempotent migrations
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN status_changed_at TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN starred INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN follow_up_at TEXT")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE jobs ADD COLUMN title_hash TEXT")
        except Exception:
            pass
        try:
            conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_title_hash ON jobs(title_hash)")
        except Exception:
            pass
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS contacts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                    name TEXT NOT NULL,
                    linkedin_url TEXT,
                    role TEXT,
                    notes TEXT,
                    reached_out INTEGER NOT NULL DEFAULT 0,
                    reached_out_at TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_contacts_job ON contacts(job_id);
            """)
        except Exception:
            pass
