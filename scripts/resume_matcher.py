#!/usr/bin/env python3
"""
Resume Matcher — now delegates to  scorer but keeps legacy output.
Reads jobs/*.txt fallback and jobs.csv, outputs output/job_report.xlsx
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.config import ensure_dirs, get_settings, resolve_path
from src.resume_parser import load_profile
from src.matching.scorer import load_jobs_from_csv, score_jobs, jobs_to_dataframe

def main():
    ensure_dirs()
    print("=== Resume Matcher (compat) ===")
    profile = load_profile()
    jobs = load_jobs_from_csv("jobs/jobs.csv")
    if not jobs:
        # also try reading jobs/*.txt like original
        import os, pandas as pd
        jobs_folder = resolve_path("jobs")
        required_skills = get_settings().get("matching",{}).get("skills_master_list",[])[:12]
        results = []
        if jobs_folder.exists():
            for filename in os.listdir(jobs_folder):
                if filename.endswith(".txt"):
                    job_path = os.path.join(jobs_folder, filename)
                    with open(job_path, "r", encoding="utf-8") as file:
                        job_text = file.read().lower()
                    lines = job_text.splitlines()
                    company = "Unknown"
                    role = "Unknown"
                    for line in lines:
                        if line.startswith("company:"):
                            company = line.replace("company:", "").strip()
                        if line.startswith("role:"):
                            role = line.replace("role:", "").strip()
                    from src.models import Job
                    jobs.append(Job(id=filename, company=company, role=role, location="Remote", url=job_path, description=job_text, source="txt"))
        if not jobs:
            print("No jobs found — creating demo")
            from src.job_collector.aggregator import collect_jobs, save_jobs_csv
            jobs = collect_jobs()
            save_jobs_csv(jobs)

    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    df = jobs_to_dataframe(scored)
    # legacy expects Job File column
    df["Job File"] = df["URL"]
    cols = ["Company","Role","Job File","Match Score","Matched Skills","Missing Skills","Decision"]
    df_legacy = df[cols] if set(cols).issubset(df.columns) else df
    out = resolve_path("output/job_report.xlsx")
    out.parent.mkdir(parents=True, exist_ok=True)
    df_legacy.to_excel(out, index=False)
    print(df_legacy.head(10).to_string(index=False))
    print(f"\nReport saved to {out}")

if __name__ == "__main__":
    main()
