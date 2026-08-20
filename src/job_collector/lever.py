from __future__ import annotations
from typing import List
from .base import BaseCollector, clean_html, make_id, safe_get
from ..models import Job

class LeverCollector(BaseCollector):
    ats_name = "lever"
    def __init__(self, token: str, company: str, timeout=12, max_jobs=30):
        self.token = token
        self.company = company
        self.timeout = timeout
        self.max_jobs = max_jobs

    def fetch(self) -> List[Job]:
        url = f"https://api.lever.co/v0/postings/{self.token}?mode=json&skip=0&limit={self.max_jobs}"
        # lever also supports https://api.lever.co/v0/postings/{token}?mode=json
        try:
            r = safe_get(url, timeout=self.timeout)
            data = r.json()
            # lever returns list or dict?
            if isinstance(data, dict) and "data" in data:
                jobs = data["data"]
            elif isinstance(data, list):
                jobs = data
            else:
                jobs = []
            out: List[Job] = []
            for j in jobs[:self.max_jobs]:
                title = j.get("text", "Unknown")
                location = j.get("categories", {}).get("location", "Remote") or "Remote"
                abs_url = j.get("hostedUrl", j.get("applyUrl", f"https://jobs.lever.co/{self.token}/{j.get('id')}"))
                desc = j.get("descriptionPlain", "") or clean_html(j.get("description", "") or "")
                if not desc:
                    desc = j.get("text", "")
                out.append(Job(
                    id=str(j.get("id") or make_id(self.company, title, abs_url)),
                    company=self.company or j.get("categories", {}).get("team", self.company),
                    role=title,
                    location=location,
                    url=abs_url,
                    description=desc[:5000],
                    source="lever",
                    raw=j,
                    date_posted=j.get("createdAt"),
                ))
            return out
        except Exception as e:
            print(f"[lever:{self.token}] fetch failed: {e}")
            return []
