from __future__ import annotations
import abc
import hashlib
import re
import time
from typing import List
import requests
from ..models import Job

class BaseCollector(abc.ABC):
    ats_name: str = "base"
    def fetch(self) -> List[Job]:
        raise NotImplementedError

def clean_html(s: str) -> str:
    if not s:
        return ""
    # strip html tags
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def make_id(company: str, role: str, url: str) -> str:
    base = f"{company}|{role}|{url}"
    return hashlib.md5(base.encode()).hexdigest()[:12]

def safe_get(url: str, timeout=12, headers=None, retries=2):
    hdrs = {"User-Agent": "AI-Job-Agent/1.0"}
    if headers:
        hdrs.update(headers)
    for attempt in range(retries+1):
        try:
            r = requests.get(url, timeout=timeout, headers=hdrs)
            if r.status_code == 429:
                time.sleep(2 + attempt*2)
                continue
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == retries:
                raise
            time.sleep(1)
    return None
