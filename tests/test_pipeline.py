"""Smoke test — like AI Job Agent's end-to-end check (offline-safe)"""
import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.models import Job
from src.job_collector.aggregator import DEMO_JOBS
from src.resume_parser import load_profile
from src.matching.scorer import score_jobs
from src.tailoring.engine import tailor_for_job

def demo_jobs():
    jobs = []
    for row in DEMO_JOBS:
        jobs.append(Job(
            id=row["URL"].split("/")[-1],
            company=row["Company"],
            role=row["Role"],
            location=row["Location"],
            url=row["URL"],
            description=row["Description"],
            source=row["Source"],
        ))
    return jobs

def test_score():
    jobs = demo_jobs()
    profile = load_profile()
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    assert len(scored) == len(jobs)
    assert scored[0].match_score >= scored[-1].match_score
    for s in scored:
        assert len(s.matched_skills) == len(set(s.matched_skills)), "duplicate matched_skills"
    print(f"score ok: top {scored[0].company} {scored[0].match_score}")

def test_tailor():
    jobs = demo_jobs()
    profile = load_profile()
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    top = scored[0]
    resume, cover, diff = tailor_for_job(profile, top)
    assert len(resume) > 200
    assert len(cover) > 100
    assert len(diff) > 10
    print("tailor ok")

def test_no_duplicate_skills():
    from src.config import get_settings
    master = get_settings().get("matching",{}).get("skills_master_list",[])
    assert len(master) == len(set([s.lower() for s in master])), "master list has duplicates"

if __name__ == "__main__":
    test_no_duplicate_skills()
    print("no dup ok")
    test_score()
    test_tailor()
    print("ALL TESTS PASSED")
