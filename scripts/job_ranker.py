#!/usr/bin/env python3
"""
Job Ranker —  skill + TF-IDF scorer
Backward compatible: still outputs output/ranked_jobs.xlsx with same columns plus extras.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.config import ensure_dirs
from src.resume_parser import load_profile
from src.matching.scorer import load_jobs_from_csv, score_jobs, save_ranked

def main():
    ensure_dirs()
    print("=== Job Ranker (AI Job Agent scoring) ===")
    profile = load_profile()
    print(f"Resume: {profile.name} — skills {profile.skills}")
    jobs = load_jobs_from_csv("jobs/jobs.csv")
    if not jobs:
        print("No jobs found in jobs/jobs.csv — running collector...")
        from src.job_collector.aggregator import collect_jobs, save_jobs_csv
        jobs = collect_jobs()
        save_jobs_csv(jobs)
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    xlsx, df = save_ranked(scored)
    print(df[["Company","Role","Match Score","Matched Skills","Missing Skills","Decision"]].head(10).to_string(index=False))
    print(f"\nRanked {len(scored)} jobs -> {xlsx}")

if __name__ == "__main__":
    main()
