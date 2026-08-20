from __future__ import annotations
import csv
import json
import pathlib
from datetime import datetime
from typing import List, Dict
import pandas as pd

from ..config import resolve_path, get_settings, ensure_dirs
from ..models import ApplicationRecord, ScoredJob

def tracker_path() -> pathlib.Path:
    cfg = get_settings()
    return resolve_path(cfg.get("apply", {}).get("tracker_path", "output/applications.csv"))

def receipts_dir() -> pathlib.Path:
    cfg = get_settings()
    p = resolve_path(cfg.get("apply", {}).get("receipts_dir", "output/receipts"))
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_applications() -> List[Dict]:
    p = tracker_path()
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p, dtype=str).fillna("")
        return df.to_dict(orient="records")
    except Exception:
        return []

def was_already_applied(url: str) -> bool:
    apps = load_applications()
    return any(a.get("url")==url or a.get("URL")==url for a in apps)

def record_application(job: ScoredJob, status: str, resume_path: str = "", cover_path: str = "", receipt_path: str = "", answers: dict = None, error: str = ""):
    p = tracker_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    file_exists = p.exists()
    fieldnames = ["id","company","role","location","url","match_score","status","applied_at","resume_path","cover_letter_path","receipt_path","ats","error"]
    now = datetime.utcnow().isoformat()
    row = {
        "id": job.id,
        "company": job.company,
        "role": job.role,
        "location": job.location,
        "url": job.url,
        "match_score": job.match_score,
        "status": status,
        "applied_at": now if status in ("applied","failed","queued","approved","skipped") else "",
        "resume_path": resume_path,
        "cover_letter_path": cover_path,
        "receipt_path": receipt_path,
        "ats": job.source,
        "error": error or "",
    }
    # append
    with open(p, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists or p.stat().st_size == 0:
            w.writeheader()
        w.writerow(row)
    return row

def update_status(job_id: str, new_status: str):
    p = tracker_path()
    if not p.exists():
        return
    df = pd.read_csv(p, dtype=str).fillna("")
    df.loc[df["id"]==job_id, "status"] = new_status
    df.loc[df["id"]==job_id, "applied_at"] = datetime.utcnow().isoformat()
    df.to_csv(p, index=False)

def save_receipt(job: ScoredJob, resume_path: str, cover_path: str, answers: dict, status: str = "applied") -> pathlib.Path:
    rd = receipts_dir()
    safe = f"{job.company}_{job.role}_{job.id[:6]}".replace(" ","_").replace("/","_")
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in safe)[:60]
    receipt = {
        "id": job.id,
        "company": job.company,
        "role": job.role,
        "location": job.location,
        "url": job.url,
        "ats": job.source,
        "match_score": job.match_score,
        "matched_skills": job.matched_skills,
        "missing_skills": job.missing_skills,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "resume_path": resume_path,
        "cover_letter_path": cover_path,
        "answers": answers or {},
        "fields_filled": {
            "full_name": "from profile",
            "email": "from profile",
            "phone": "from profile",
            "resume": resume_path,
            "cover_letter": cover_path,
        },
        "ai_disclosure": "This application was tailored by AI and approved by the candidate.",
    }
    path = rd / f"{safe}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    # also html
    html = rd / f"{safe}.html"
    html.write_text(f"<h1>Application Receipt</h1><p>{job.role} at {job.company}</p><p>Status: {status}</p><p>Score: {job.match_score}</p><p>URL: <a href='{job.url}'>{job.url}</a></p><pre>{json.dumps(receipt, indent=2)}</pre>", encoding="utf-8")
    return path

def get_stats():
    apps = load_applications()
    from collections import Counter
    cnt = Counter(a.get("status","") for a in apps)
    return {"total": len(apps), "by_status": dict(cnt)}
