#!/usr/bin/env python3
"""
OpenAI Resume Tailor — now powered by  engine
Handles both LLM and template fallback so it works without API key.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.config import ensure_dirs, get_settings
from src.resume_parser import load_profile
from src.matching.scorer import load_jobs_from_csv, score_jobs
from src.tailoring.engine import tailor_for_job, save_tailored, generate_prompt_file

def main():
    ensure_dirs()
    print("=== OpenAI Resume Tailor () ===")
    profile = load_profile()
    jobs = load_jobs_from_csv()
    if not jobs:
        print("No jobs in jobs/jobs.csv — run real_job_collector first")
        from src.job_collector.aggregator import collect_jobs, save_jobs_csv
        jobs = collect_jobs()
        save_jobs_csv(jobs)
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    if not scored:
        print("no scored jobs")
        return
    top = scored[0]
    print(f"Tailoring for top job: {top.role} at {top.company} ({top.match_score}%)")
    resume_text, cover, diff = tailor_for_job(profile, top)
    rp, cp, dp, docx = save_tailored(top, resume_text, cover, diff)
    print(f"Tailored resume -> {rp}")
    print(f"Cover letter   -> {cp}")
    print(f"Diff           -> {dp}")
    print(f"Docx           -> {docx}")
    # also show preview
    print("\n--- RESUME PREVIEW (first 800 chars) ---")
    print(resume_text[:800])
    print("\n--- COVER LETTER ---")
    print(cover[:800])
    print("\n--- DIFF ---")
    print(diff[:1200])
    generate_prompt_file(top, profile)

if __name__ == "__main__":
    main()
