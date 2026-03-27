from typing import Optional
from pydantic import BaseModel


class Job(BaseModel):
    id: int
    source: str
    url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    remote_type: Optional[str] = None
    salary_raw: Optional[str] = None
    description: Optional[str] = None
    posted_at: Optional[str] = None
    scraped_at: str
    status: str
    notes: Optional[str] = None
    applied_at: Optional[str] = None
    cv_score: Optional[float] = None
    cv_score_rationale: Optional[str] = None
    cv_score_breakdown: Optional[str] = None
    cv_scored_at: Optional[str] = None
    status_changed_at: Optional[str] = None
    starred: int = 0
    follow_up_at: Optional[str] = None
    created_at: str
    updated_at: str


class JobSummary(BaseModel):
    id: int
    source: str
    url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    remote_type: Optional[str] = None
    salary_raw: Optional[str] = None
    posted_at: Optional[str] = None
    scraped_at: str
    status: str
    cv_score: Optional[float] = None
    cv_scored_at: Optional[str] = None
    cv_score_rationale: Optional[str] = None
    cv_score_breakdown: Optional[str] = None
    starred: int = 0
    follow_up_at: Optional[str] = None
    has_description: bool = False


class JobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    applied_at: Optional[str] = None
    starred: Optional[int] = None
    follow_up_at: Optional[str] = None


class JobsResponse(BaseModel):
    items: list[JobSummary]
    total: int


class ScrapingRunDetail(BaseModel):
    id: int
    run_id: int
    source: str
    status: str
    jobs_found: int
    jobs_new: int
    error_msg: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None


class ScrapingRun(BaseModel):
    id: int
    started_at: str
    finished_at: Optional[str] = None
    status: str
    details: list[ScrapingRunDetail] = []


class ScoreResult(BaseModel):
    cv_score: float
    cv_score_rationale: str
    cv_score_breakdown: Optional[str] = None
    strengths: list[str] = []
    gaps: list[str] = []


class StatsResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_source: dict[str, int]
    unscored: int


class Contact(BaseModel):
    id: int
    job_id: int
    name: str
    linkedin_url: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None
    reached_out: int = 0
    reached_out_at: Optional[str] = None
    created_at: str
    updated_at: str


class ContactCreate(BaseModel):
    name: str
    linkedin_url: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    linkedin_url: Optional[str] = None
    role: Optional[str] = None
    notes: Optional[str] = None
    reached_out: Optional[int] = None
