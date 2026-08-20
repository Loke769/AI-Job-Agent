#!/usr/bin/env python3
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.config import resolve_path, ensure_dirs
from src.matching.scorer import load_jobs_from_csv, score_jobs
from src.resume_parser import load_profile
from src.tailoring.engine import generate_prompt_file

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
    if not scored:
        print("no jobs to generate prompt")
        return
    top = scored[0]
    out = generate_prompt_file(top, profile)
    print(f"ChatGPT prompt saved to {out}")
    print(out.read_text(encoding="utf-8")[:1200])

if __name__ == "__main__":
    main()
