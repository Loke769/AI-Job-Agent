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
    source: str = "greenhouse"
    raw: dict = Field(default_factory=dict)

    def to_csv_row(self):
        return {
            "Company": self.company,
            "Role": self.role,
            "Location": self.location,
            "URL": self.url,
            "Description": self.description[:5000],
            "Source": self.source,
            "DatePosted": self.date_posted or "",
        }

class ScoredJob(Job):
    match_score: float = 0.0
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    tfidf_score: float = 0.0
    decision: str = ""
    fit_label: str = ""

class ResumeProfile(BaseModel):
    # Basic
    name: str = "Alex Morgan"
    first_name: str = "Alex"
    last_name: str = "Morgan"
    email: str = "alex.morgan@example.com"
    phone: str = "+1-555-010-0000"
    location: str = "Remote, United States"
    # Address — Workday asks
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = "United States"
    # Links
    linkedin: str = ""
    github: str = ""
    website: str = ""
    portfolio: str = ""
    summary: str = ""
    skills: List[str] = Field(default_factory=list)
    # Workday-style fields
    work_authorization: str = "US Citizen"
    require_sponsorship: str = "No"
    visa_type: str = ""
    sponsorship_details: str = ""
    gender: str = ""
    ethnicity: str = ""
    veteran_status: str = ""
    disability_status: str = ""
    salary_expectation: str = "Open"
    notice_period: str = "2 weeks"
    willing_to_relocate: str = "Yes"
    # Education & Experience
    education: List[dict] = Field(default_factory=list)
    experience: List[dict] = Field(default_factory=list)
    raw_text: str = ""
    base_resume_path: str = "resumes/master_resume.docx"
    # Gmail connector mock
    gmail_connected: bool = False
    gmail_email: str = ""

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
    status: str = "queued"
    applied_at: Optional[str] = None
    resume_path: Optional[str] = None
    cover_letter_path: Optional[str] = None
    receipt_path: Optional[str] = None
    ats: str = ""
    answers: dict = Field(default_factory=dict)
    jd_text: str = ""
    error: Optional[str] = None
    # Gmail tracking
    gmail_thread_id: str = ""
    email_status: str = ""  # e.g., "Application received via Gmail"
