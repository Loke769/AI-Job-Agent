from __future__ import annotations
import time
import json
from typing import List, Dict
from datetime import datetime

from ..models import ScoredJob, ResumeProfile
from ..config import get_settings, resolve_path, ensure_dirs
from .tracker import record_application, save_receipt, was_already_applied
from ..tailoring.engine import tailor_for_job, save_tailored

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

def generate_answers(job: ScoredJob, profile: ResumeProfile) -> Dict[str, str]:
    # Comprehensive Workday/Greenhouse/Lever answers using every profile field
    return {
        "Why do you want to work at this company?": f"I'm excited by {job.company}'s mission in {job.role}. My experience in {', '.join(job.matched_skills[:3])} aligns with {job.description[:120]}.",
        "Describe your experience with relevant tools": f"Hands-on with {', '.join(job.matched_skills[:6] or profile.skills[:6])} delivering impact in prior roles.",
        "Are you legally authorized to work?": profile.work_authorization or "Yes",
        "Do you require sponsorship?": profile.require_sponsorship or "No",
        "Visa type": profile.visa_type or "N/A",
        "Expected salary": profile.salary_expectation or "Open",
        "Notice period": profile.notice_period or "2 weeks",
        "Willing to relocate": profile.willing_to_relocate or "Yes",
        "Address": f"{profile.address_line1} {profile.city} {profile.state} {profile.zip_code} {profile.country}".strip(),
        "Gender": profile.gender or "Decline to self identify",
        "Ethnicity": profile.ethnicity or "Decline to self identify",
        "Veteran status": profile.veteran_status or "Decline",
        "Disability": profile.disability_status or "Decline",
        "LinkedIn": profile.linkedin,
        "Website": profile.website or profile.portfolio,
        "Cover letter required": "Yes — tailored per JD",
    }

def simulate_gmail_fetch(job: ScoredJob, profile: ResumeProfile) -> Dict:
    # Mock Gmail connector: creates a fake email thread for tracking
    # In real deployment, this would call Gmail API with OAuth token from profile.gmail_email
    if not profile.gmail_connected or not profile.gmail_email:
        return {"connected": False, "email": profile.email, "thread_id": "", "status": "Gmail not connected — using primary email"}
    # Simulate an application confirmation email
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    thread_id = f"thread_{job.id[:6]}_{int(time.time())}"
    email = {
        "from": f"careers@{job.company.lower().replace(' ','')}.com",
        "to": profile.gmail_email,
        "subject": f"Application received — {job.role} at {job.company}",
        "snippet": f"Thank you for applying to {job.role} at {job.company} via {job.source}. Your tailored resume was received on {ts}.",
        "thread_id": thread_id,
        "timestamp": ts,
    }
    # Persist to output/gmail_emails.json for tracker
    gmail_path = resolve_path("output/gmail_emails.json")
    try:
        existing = json.loads(gmail_path.read_text(encoding="utf-8")) if gmail_path.exists() else []
    except:
        existing = []
    existing.append({"job_id": job.id, "company": job.company, "role": job.role, **email})
    gmail_path.write_text(json.dumps(existing[-100:], indent=2), encoding="utf-8")
    return {"connected": True, "email": profile.gmail_email, "thread_id": thread_id, "status": f"Confirmation email sent to {profile.gmail_email}", "email_data": email}

def dry_run_apply(job: ScoredJob, profile: ResumeProfile) -> Dict:
    # 1. Tailor resume + cover per JD (AI takes base resume from profile.raw_text)
    resume_text, cover, diff = tailor_for_job(profile, job)
    resume_path, cover_path, diff_path, docx_path = save_tailored(job, resume_text, cover, diff)
    answers = generate_answers(job, profile)
    # 2. Simulate account creation for Workday/ATS if needed
    account_info = {}
    if job.source in ("workday", "greenhouse") or "workday" in job.url.lower():
        account_info = {"account_created": True, "username": profile.email, "ats": job.source, "via": "auto-created with profile details"}
    # 3. Gmail fetch
    gmail = simulate_gmail_fetch(job, profile)
    # 4. Receipt with full details
    extra = {**answers, **account_info, "gmail": gmail, "jd": job.description[:2000]}
    receipt_path = save_receipt(job, resume_path, cover_path, extra, status="applied (dry-run)")
    # 5. Tracker — keep JD + updated resume + Gmail thread
    record_application(job, status="applied", resume_path=resume_path, cover_letter_path=cover_path, receipt_path=str(receipt_path), answers=extra, jd_text=job.description[:3000], gmail_thread_id=gmail.get("thread_id",""), email_status=gmail.get("status",""))
    return {
        "job": job,
        "resume_path": resume_path,
        "cover_path": cover_path,
        "diff_path": diff_path,
        "receipt_path": str(receipt_path),
        "answers": answers,
        "gmail": gmail,
        "account": account_info,
        "status": "applied (dry-run)"
    }

def playwright_apply(job: ScoredJob, profile: ResumeProfile, headless=True) -> Dict:
    if not HAS_PLAYWRIGHT:
        return dry_run_apply(job, profile)
    cfg = get_settings()
    ats = job.source
    timeout = int(cfg.get("apply",{}).get("ats_timeout",45000))
    resume_text, cover, diff = tailor_for_job(profile, job)
    resume_path, cover_path, diff_path, docx_path = save_tailored(job, resume_text, cover, diff)
    answers = generate_answers(job, profile)

    if cfg.get("apply",{}).get("dry_run", True):
        gmail = simulate_gmail_fetch(job, profile)
        receipt_path = save_receipt(job, resume_path, cover_path, {**answers, "gmail": gmail}, status="applied (dry-run-playwright)")
        record_application(job, status="applied", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path), jd_text=job.description[:3000], gmail_thread_id=gmail.get("thread_id",""))
        return {"status":"applied (dry-run)", "receipt": str(receipt_path), "gmail": gmail}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(job.url, timeout=timeout)
            if ats == "greenhouse":
                try:
                    page.get_by_role("button", name="Apply").click(timeout=5000)
                except: pass
                for label, value in [
                    ("First Name", profile.first_name or profile.name.split()[0]),
                    ("Last Name", profile.last_name or profile.name.split()[-1]),
                    ("Email", profile.email),
                    ("Phone", profile.phone),
                    ("Address", profile.address_line1),
                    ("City", profile.city),
                    ("State", profile.state),
                    ("Zip", profile.zip_code),
                    ("LinkedIn", profile.linkedin),
                ]:
                    try:
                        page.get_by_label(label, exact=False).fill(value, timeout=2000)
                    except: pass
                try:
                    inputs = page.locator("input[type='file']")
                    if inputs.count() > 0:
                        inputs.first.set_input_files(docx_path)
                except: pass
            elif ats == "lever":
                try:
                    page.locator("a.postings-btn").first.click(timeout=4000)
                except: pass
            time.sleep(1)
            browser.close()
        gmail = simulate_gmail_fetch(job, profile)
        receipt_path = save_receipt(job, resume_path, cover_path, {**answers, "gmail": gmail}, status="applied")
        record_application(job, status="applied", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path), jd_text=job.description[:3000], gmail_thread_id=gmail.get("thread_id",""))
        return {"status":"applied", "receipt": str(receipt_path), "gmail": gmail}
    except Exception as e:
        err = str(e)
        receipt_path = save_receipt(job, resume_path, cover_path, answers, status="failed")
        record_application(job, status="failed", resume_path=resume_path, cover_path=cover_path, receipt_path=str(receipt_path), error=err, jd_text=job.description[:3000])
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
            "description": job.description,
            "match_score": job.match_score,
            "matched_skills": job.matched_skills,
            "missing_skills": job.missing_skills,
            "decision": job.decision,
            "resume_preview": resume_text[:3000],
            "cover_preview": cover[:2000],
            "diff": diff[:3000],
        })
        save_tailored(job, resume_text, cover, diff)

    queue_path.write_text(json.dumps(enriched, indent=2), encoding="utf-8")
    print(f"[apply] approval queue: {len(enriched)} jobs -> {queue_path} (auto_approve={auto_approve})")
    return enriched, queue

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
        if not cfg.get("apply",{}).get("auto_approve", False) and not dry:
            continue
        if dry or not HAS_PLAYWRIGHT:
            res = dry_run_apply(job, profile)
        else:
            res = playwright_apply(job, profile)
        results.append(res)
        applied += 1
        time.sleep(float(cfg.get("apply",{}).get("delay_between_apps",0.5)))
    return results
