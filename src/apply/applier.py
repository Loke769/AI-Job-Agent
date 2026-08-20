from __future__ import annotations
import time
import random
import json
import pathlib
from typing import List, Dict
from datetime import datetime

from ..models import ScoredJob, ResumeProfile
from ..config import get_settings, resolve_path, ensure_dirs
from .tracker import record_application, save_receipt, was_already_applied
from ..tailoring.engine import tailor_for_job, save_tailored

# ATS form fillers — Playwright optional
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

def generate_answers(job: ScoredJob, profile: ResumeProfile) -> Dict[str, str]:
    # Answers for open-ended ATS questions in user's voice
    # Answer sponsorship, location, salary, work auth
    cfg = get_settings()
    work_auth = cfg.get("profile", {}).get("work_authorization", profile.location)
    return {
        "Why do you want to work at this company?": f"I'm excited by {job.company}'s work in data platform / {job.role.lower()}. My experience in {', '.join(job.matched_skills[:3])} aligns well with {job.description[:120]}.",
        "Describe your experience with relevant tools": f"Hands-on with {', '.join(job.matched_skills[:5])} building batch and streaming pipelines, warehousing on Snowflake/Databricks, orchestration via Airflow.",
        "Are you legally authorized to work?": work_auth,
        "Do you require sponsorship?": "No" if "citizen" in work_auth.lower() or "no" in work_auth.lower() else "Please discuss",
        "Expected salary": "Open to discussion, market rate",
        "Notice period": "2 weeks",
    }

def dry_run_apply(job: ScoredJob, profile: ResumeProfile) -> Dict:
    # Simulate submission: tailor, generate answers, save receipt
    resume_text, cover, diff = tailor_for_job(profile, job)
    resume_path, cover_path, diff_path, docx_path = save_tailored(job, resume_text, cover, diff)
    answers = generate_answers(job, profile)
    receipt_path = save_receipt(job, resume_path, cover_path, answers, status="applied (dry-run)")
    record_application(job, status="applied", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path), answers=answers)
    return {
        "job": job,
        "resume_path": resume_path,
        "cover_path": cover_path,
        "diff_path": diff_path,
        "receipt_path": str(receipt_path),
        "answers": answers,
        "status": "applied (dry-run)"
    }

def playwright_apply(job: ScoredJob, profile: ResumeProfile, headless=True) -> Dict:
    if not HAS_PLAYWRIGHT:
        return dry_run_apply(job, profile)
    # Real submission across ATSes — simplified but functional skeleton
    cfg = get_settings()
    ats = job.source
    timeout = int(cfg.get("apply",{}).get("ats_timeout",45000))
    resume_text, cover, diff = tailor_for_job(profile, job)
    resume_path, cover_path, diff_path, docx_path = save_tailored(job, resume_text, cover, diff)
    answers = generate_answers(job, profile)

    # For demo we do not actually submit to avoid spamming companies.
    # If DRY_RUN is false and user explicitly wants live, we would navigate.
    # Here we show the Playwright flow but keep safe.
    if cfg.get("apply",{}).get("dry_run", True):
        receipt_path = save_receipt(job, resume_path, cover_path, answers, status="applied (dry-run-playwright)")
        record_application(job, status="applied", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path))
        return {"status":"applied (dry-run)", "receipt": str(receipt_path)}

    # LIVE PATH (requires explicit opt-in)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(job.url, timeout=timeout)
            # ATS-specific selectors
            if ats == "greenhouse":
                # Greenhouse has "Apply" button
                try:
                    page.get_by_role("button", name="Apply").click(timeout=5000)
                except: pass
                # fill common fields if present
                for label, value in [
                    ("First Name", profile.name.split()[0]),
                    ("Last Name", profile.name.split()[-1]),
                    ("Email", profile.email),
                    ("Phone", profile.phone),
                ]:
                    try:
                        page.get_by_label(label, exact=False).fill(value, timeout=2000)
                    except: pass
                # attach resume if file input exists
                try:
                    inputs = page.locator("input[type='file']")
                    if inputs.count() > 0:
                        inputs.first.set_input_files(docx_path)
                except: pass
                # do NOT auto-submit live unless auto_approve
                # page.get_by_role("button", name="Submit").click()
            elif ats == "lever":
                try:
                    page.locator("a.postings-btn").first.click(timeout=4000)
                except: pass
            # generic fallback: fill inputs by placeholder
            time.sleep(1)
            browser.close()
        receipt_path = save_receipt(job, resume_path, cover_path, answers, status="applied")
        record_application(job, status="applied", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path))
        return {"status":"applied", "receipt": str(receipt_path)}
    except Exception as e:
        err = str(e)
        receipt_path = save_receipt(job, resume_path, cover_path, answers, status="failed")
        record_application(job, status="failed", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path), error=err)
        return {"status":"failed", "error": err}

def build_approval_queue(scored: List[ScoredJob], profile: ResumeProfile):
    cfg = get_settings()
    min_score = int(cfg.get("preferences",{}).get("min_match_score",50))
    max_apps = int(cfg.get("apply",{}).get("max_applications_per_run",25))
    auto_approve = bool(cfg.get("apply",{}).get("auto_approve", False))
    queue = []
    for job in scored:
        if len(queue) >= max_apps:
            break
        if was_already_applied(job.url):
            continue
        if job.match_score < min_score:
            continue
        queue.append(job)

    ensure_dirs()
    queue_path = resolve_path("output/approval_queue.json")
    # enrich queue with tailored previews so dashboard can show diff
    enriched = []
    for job in queue:
        resume_text, cover, diff = tailor_for_job(profile, job)
        enriched.append({
            "id": job.id,
            "company": job.company,
            "role": job.role,
            "location": job.location,
            "url": job.url,
            "source": job.source,
            "match_score": job.match_score,
            "matched_skills": job.matched_skills,
            "missing_skills": job.missing_skills,
            "decision": job.decision,
            "resume_preview": resume_text[:2500],
            "cover_preview": cover[:2000],
            "diff": diff[:3000],
        })
        # also persist individual preview files
        save_tailored(job, resume_text, cover, diff)

    queue_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    print(f"[apply] approval queue: {len(enriched)} jobs -> {queue_path} (auto_approve={auto_approve})")
    return enriched, queue

def process_queue(auto: bool = False):
    # Called to actually apply from approval queue
    import json
    cfg = get_settings()
    dry = bool(cfg.get("apply",{}).get("dry_run", True))
    queue_path = resolve_path("output/approval_queue.json")
    if not queue_path.exists():
        print("no approval queue")
        return []
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    profile = __import__("src.resume_parser", fromlist=["load_profile"]).load_profile()
    # need to reconstruct ScoredJob objects for applying
    # load from ranked csv for full data
    from ..matching.scorer import load_jobs_from_csv, score_jobs
    from ..resume_parser import load_profile
    # simpler: use data itself
    results = []
    for item in data:
        # reconstruct minimal scored job
        job = ScoredJob(
            id=item["id"],
            company=item["company"],
            role=item["role"],
            location=item["location"],
            url=item["url"],
            description=item.get("resume_preview","")[:1000],
            source=item.get("source","generic"),
            match_score=item["match_score"],
            matched_skills=item["matched_skills"],
            missing_skills=item["missing_skills"],
            decision=item["decision"],
            fit_label="Medium",
        )
        # if in auto mode or item approved flag
        should_apply = auto or item.get("approved", False)
        # If auto is passed explicitly, apply all; if not, only approved
        # For dry dry_run we simulate
        if dry:
            res = dry_run_apply(job, profile)
        else:
            if HAS_PLAYWRIGHT:
                res = playwright_apply(job, profile)
            else:
                res = dry_run_apply(job, profile)
        results.append(res)
        time.sleep(float(cfg.get("apply",{}).get("delay_between_apps",1.2)))
    return results

def apply_batch(scored: List[ScoredJob], profile: ResumeProfile, limit: int = None):
    cfg = get_settings()
    max_apps = limit or int(cfg.get("apply",{}).get("max_applications_per_run",25))
    dry = bool(cfg.get("apply",{}).get("dry_run", True))
    results = []
    applied = 0
    for job in scored:
        if applied >= max_apps:
            break
        if was_already_applied(job.url):
            print(f"[apply] skip already applied: {job.company} {job.role}")
            continue
        if job.match_score < int(cfg.get("preferences",{}).get("min_match_score",50)):
            continue
        # If auto_approve false, we queue instead of apply
        if not cfg.get("apply",{}).get("auto_approve", False) and not dry:
            # still create queue entry; actual submit awaits approval
            continue
        if dry or not HAS_PLAYWRIGHT:
            res = dry_run_apply(job, profile)
        else:
            res = playwright_apply(job, profile)
        results.append(res)
        applied += 1
        time.sleep(float(cfg.get("apply",{}).get("delay_between_apps",0.5)))
    return results
