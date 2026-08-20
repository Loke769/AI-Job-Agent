from __future__ import annotations
import re
from typing import List
from .base import BaseCollector, clean_html, make_id, safe_get
from ..models import Job

class GreenhouseCollector(BaseCollector):
    ats_name = "greenhouse"
    def __init__(self, token: str, company: str, timeout=12, max_jobs=30):
        self.token = token
        self.company = company
        self.timeout = timeout
        self.max_jobs = max_jobs

    def fetch(self) -> List[Job]:
        url = f"https://boards-api.greenhouse.io/v1/boards/{self.token}/jobs"
        try:
            r = safe_get(url, timeout=self.timeout)
            data = r.json()
            jobs = data.get("jobs", [])
            out: List[Job] = []
            for j in jobs[:self.max_jobs]:
                title = j.get("title", "Unknown")
                location = (j.get("location") or {}).get("name", "Remote")
                abs_url = j.get("absolute_url", f"https://boards.greenhouse.io/{self.token}/jobs/{j.get('id')}")
                content = j.get("content", "") or ""
                # content is html
                desc = clean_html(content)
                if not desc:
                    desc = title
                # filter empty?
                out.append(Job(
                    id=str(j.get("id") or make_id(self.company, title, abs_url)),
                    company=self.company,
                    role=title,
                    location=location,
                    url=abs_url,
                    description=desc[:5000],
                    source="greenhouse",
                    raw=j,
                    date_posted=j.get("updated_at") or j.get("created_at"),
                ))
            return out
        except Exception as e:
            print(f"[greenhouse:{self.token}] fetch failed: {e}")
            return []
