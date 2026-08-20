#!/usr/bin/env python3
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.config import resolve_path, ensure_dirs
from src.matching.scorer import load_jobs_from_csv, score_jobs
from src.resume_parser import load_profile

def main():
    ensure_dirs()
    profile = load_profile()
    jobs = load_jobs_from_csv()
    if not jobs:
        from src.job_collector.aggregator import collect_jobs, save_jobs_csv
        jobs = collect_jobs()
        save_jobs_csv(jobs)
        jobs = load_jobs_from_csv()
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    top = scored[0] if scored else None
    company = top.company if top else "Target Company"
    role = top.role if top else "Target Role"
    matched = ", ".join(top.matched_skills) if top and top.matched_skills else ", ".join(profile.skills[:5])
    summary = f"{role} candidate with experience in {matched}. Experienced in building solutions, collaborating across teams, and delivering measurable impact. Interested in contributing to {company} as {role}."
    print("Generated Resume Summary:")
    print(summary)
    out = resolve_path("output/generated_summary.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(summary, encoding="utf-8")
    print(f"Summary saved to {out}")

if __name__ == "__main__":
    main()
