#!/usr/bin/env python3
"""
Real Job Collector —  50k+ career pages watcher
Now fetches from Greenhouse / Lever / Ashby public APIs with demo fallback.
"""
import pathlib
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.config import ensure_dirs
from src.job_collector.aggregator import collect_jobs, save_jobs_csv

def main():
    ensure_dirs()
    print("=== Real Job Collector (AI Job Agent 50k+ watcher) ===")
    print("Fetching from Greenhouse / Lever / Ashby boards...")
    jobs = collect_jobs(max_per_source=12, max_total=80)
    path = save_jobs_csv(jobs)
    print(f"Done: {len(jobs)} jobs -> {path}")
    # preview top
    for j in jobs[:5]:
        print(f"  - {j.company:15s} | {j.role:30s} | {j.location:20s} | {j.source}")

if __name__ == "__main__":
    main()
