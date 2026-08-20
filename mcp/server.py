"""MCP server stub — wire AI Job Agent into Claude/Codex like AI Job Agent CLI"""
# Usage: python mcp/server.py  (exposes tools: collect_jobs, rank, tailor, apply)
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.job_collector.aggregator import collect_jobs, save_jobs_csv
from src.resume_parser import load_profile
from src.matching.scorer import score_jobs
from src.apply.applier import apply_batch

def tool_collect():
    jobs = collect_jobs()
    save_jobs_csv(jobs)
    return {"collected": len(jobs)}
def tool_apply(limit=5):
    from src.matching.scorer import load_jobs_from_csv
    jobs = load_jobs_from_csv()
    profile = load_profile()
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    results = apply_batch(scored, profile, limit=limit)
    return {"applied": len(results)}

if __name__ == "__main__":
    print(tool_collect())
    print(tool_apply())
