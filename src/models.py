from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import pathlib

class Job(BaseModel):
    id: str = Field(default_factory=lambda: "")
    company: str
    role: str
    location: str = "Remote"
    url: str
    description: str = ""
    department: str = ""
    employment_type: str = ""
    date_posted: Optional[str] = None
    source: str = "greenhouse"  # greenhouse | lever | ashby | workday | generic
    raw: dict = Field(default_factory=dict)

    def to_csv_row(self):
        return {
            "Company": self.company,
            "Role": self.role,
            "Location": self.location,
            "URL": self.url,
            "Description": self.description[:5000],  # csv safe
            "Source": self.source,
            "DatePosted": self.date_posted or "",
        }

class ScoredJob(Job):
    match_score: float = 0.0
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    tfidf_score: float = 0.0
    decision: str = ""
    fit_label: str = ""  # Strong / Medium / Weak

class ResumeProfile(BaseModel):
    name: str = "Alex Morgan"
    email: str = "alex.morgan@example.com"
    phone: str = "+1-555-010-0000"
    location: str = "Remote, United States"
    linkedin: str = ""
    github: str = ""
    website: str = ""
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    experience: List[dict] = Field(default_factory=list)
    education: List[dict] = Field(default_factory=list)
    raw_text: str = ""

class TailoredDoc(BaseModel):
    job_id: str
    company: str
    role: str
    resume_text: str
    cover_letter: str
    diff_summary: str
    resume_path: str
    cover_letter_path: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class ApplicationRecord(BaseModel):
    id: str
    company: str
    role: str
    location: str
    url: str
    match_score: float
    status: str = "queued"  # queued | approved | applied | failed | skipped
    applied_at: Optional[str] = None
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    receipt_path: Optional[str] = None
    ats: str = ""
    answers: dict = Field(default_factory=dict)
    error: Optional[str] = None
