from fastapi import APIRouter, HTTPException
from datetime import datetime

from ..database import db
from ..schemas import Contact, ContactCreate, ContactUpdate
from ..services.contacts import get_search_links

router = APIRouter(prefix="/api", tags=["contacts"])


@router.get("/jobs/{job_id}/search-links")
def search_links(job_id: int):
    with db() as conn:
        job = conn.execute("SELECT company, title FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    company = job["company"] or ""
    title = job["title"] or ""
    return get_search_links(company, title)


@router.get("/jobs/{job_id}/contacts", response_model=list[Contact])
def list_contacts(job_id: int):
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@router.post("/jobs/{job_id}/contacts", response_model=Contact, status_code=201)
def add_contact(job_id: int, payload: ContactCreate):
    with db() as conn:
        job = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        now = datetime.utcnow().isoformat()
        cur = conn.execute(
            """INSERT INTO contacts (job_id, name, linkedin_url, role, notes, reached_out, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, 0, ?, ?)""",
            (job_id, payload.name, payload.linkedin_url, payload.role, payload.notes, now, now),
        )
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@router.patch("/contacts/{contact_id}", response_model=Contact)
def update_contact(contact_id: int, payload: ContactUpdate):
    updates = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    now = datetime.utcnow().isoformat()
    if "reached_out" in updates and updates["reached_out"]:
        updates.setdefault("reached_out_at", now)
    updates["updated_at"] = now
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [contact_id]
    with db() as conn:
        conn.execute(f"UPDATE contacts SET {set_clause} WHERE id = ?", values)
        row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Contact not found")
    return dict(row)


@router.delete("/contacts/{contact_id}", status_code=204)
def delete_contact(contact_id: int):
    with db() as conn:
        conn.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))
