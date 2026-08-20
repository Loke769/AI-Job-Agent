from __future__ import annotations
from typing import List
from .base import BaseCollector, clean_html, make_id, safe_get
from ..models import Job

class AshbyCollector(BaseCollector):
    ats_name = "ashby"
    def __init__(self, token: str, company: str, timeout=12, max_jobs=30):
        self.token = token
        self.company = company
        self.timeout = timeout
        self.max_jobs = max_jobs

    def fetch(self) -> List[Job]:
        # Public Ashby posting api: https://api.ashbyhq.com/posting-api/job-board/{token}
        # Query param ?page=1
        url = f"https://api.ashbyhq.com/posting-api/job-board/{self.token}"
        try:
            r = safe_get(url, timeout=self.timeout)
            data = r.json()
            jobs = data.get("jobs", [])
            out: List[Job] = []
            for j in jobs[:self.max_jobs]:
                title = j.get("title", "Unknown")
                location = j.get("location", "Remote") or "Remote"
                abs_url = j.get("jobUrl", f"https://jobs.ashbyhq.com/{self.token}/{j.get('id')}")
                desc = clean_html(j.get("descriptionHtml", "") or "") or j.get("descriptionPlain", "") or title
                out.append(Job(
                    id=str(j.get("id") or make_id(self.company, title, abs_url)),
                    company=self.company,
                    role=title,
                    location=location,
                    url=abs_url,
                    description=desc[:5000],
                    source="ashby",
                    raw=j,
                    date_posted=j.get("publishedAt"),
                ))
            return out
        except Exception as e:
            print(f"[ashby:{self.token}] fetch failed: {e}")
            return []
