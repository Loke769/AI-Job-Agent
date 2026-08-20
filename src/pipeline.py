#!/usr/bin/env python3
"""
AI Job Agent — Autonomous End-to-End Pipeline
Works for any role (engineering, data, product, design, etc.)
Usage:
  python -m src.pipeline --help
  python -m src.pipeline --once --dry-run
  python -m src.pipeline --collect-only
  python -m src.pipeline --apply --auto-approve

Flow:
  1. COLLECT  -> watches company career pages (Greenhouse/Lever/Ashby) + demo fallback
  2. PARSE    -> resume -> skills (any profession)
  3. SCORE    -> skill + TF-IDF ranking (role-agnostic)
  4. TAILOR   -> per-role resume + cover letter + diff view
  5. QUEUE    -> approval queue (human-in-the-loop)
  6. APPLY    -> ATS auto-submit (Playwright) + receipt + tracker
  7. REPORT   -> ranked xlsx/csv, tracker, receipts

All steps work offline with demo data if APIs blocked. No subscription required.
"""
from __future__ import annotations
import argparse
import time

from .config import ensure_dirs, get_settings, resolve_path
from .resume_parser import load_profile
from .job_collector.aggregator import collect_jobs, save_jobs_csv
from .matching.scorer import score_jobs, save_ranked
from .tailoring.engine import tailor_for_job, save_tailored, generate_prompt_file
from .apply.applier import build_approval_queue, apply_batch
from .apply.tracker import get_stats

def run_once(args):
    ensure_dirs()
    cfg = get_settings()
    print("="*70)
    print(" AI JOB AGENT — Autonomous Auto-Apply Pipeline ")
    print("="*70)
    print(f"dry_run={cfg.get('apply',{}).get('dry_run')} auto_approve={cfg.get('apply',{}).get('auto_approve')}")
    print(f"target_roles={cfg.get('preferences',{}).get('target_roles')}")

    # 1. Collect
    if not args.skip_collect:
        print("\n[1/6] Collecting jobs from ATS boards...")
        jobs = collect_jobs(
            max_per_source=args.max_per_source,
            max_total=args.max_total,
            use_threads=not args.no_threads,
        )
        save_jobs_csv(jobs)
    else:
        from .matching.scorer import load_jobs_from_csv
        jobs = load_jobs_from_csv()
        print(f"[1/6] Skipped collect, loaded {len(jobs)} from csv")

    if not jobs:
        print("No jobs found — abort")
        return

    # 2. Parse resume
    print("\n[2/6] Parsing resume...")
    profile = load_profile()
    print(f"  Profile: {profile.name} <{profile.email}>")
    print(f"  Skills detected: {', '.join(profile.skills[:12])} ({len(profile.skills)} total)")

    # 3. Score / Rank
    print("\n[3/6] Scoring jobs...")
    scored = score_jobs(jobs, profile.raw_text, profile.skills)
    xlsx, df = save_ranked(scored)
    print(f"  Top 3:")
    for s in scored[:3]:
        print(f"    {s.match_score:5.1f} | {s.company:15s} | {s.role:30s} | {s.decision} | matched {s.matched_skills}")

    # also keep compat output/job_report.xlsx for legacy script tests
    try:
        legacy_path = resolve_path("output/job_report.xlsx")
        df_legacy = df.rename(columns={"Match Score":"Match Score","Decision":"Decision"})[["Company","Role","Match Score","Matched Skills","Missing Skills","Decision"]]
        df_legacy["Job File"] = df["URL"]
        df_legacy.to_excel(legacy_path, index=False)
        print(f"  legacy report -> {legacy_path}")
    except Exception as e:
        print(f"legacy report failed {e}")

    # 4. Tailor top N
    print("\n[4/6] Tailoring resumes & cover letters (per-role)...")
    top_n = min(args.tailor_top, len(scored))
    for job in scored[:top_n]:
        resume_text, cover, diff = tailor_for_job(profile, job)
        rp, cp, dp, docx = save_tailored(job, resume_text, cover, diff)
        print(f"  tailored {job.company} / {job.role} -> {rp}")
    if scored:
        generate_prompt_file(scored[0], profile)
        print(f"  ChatGPT prompt -> output/chatgpt_prompt.txt")
        try:
            summary = f"{scored[0].role} candidate with experience in {', '.join(scored[0].matched_skills)}. Experienced in building solutions, collaborating across teams, and delivering impact. Interested in contributing to {scored[0].company} as {scored[0].role}."
            (resolve_path("output/generated_summary.txt")).write_text(summary, encoding="utf-8")
        except: pass

    # 5. Build approval queue (human-in-the-loop diff view)
    print("\n[5/6] Building approval queue...")
    enriched, queue = build_approval_queue(scored, profile)
    print(f"  Queue size: {len(enriched)} (threshold {cfg.get('preferences',{}).get('min_match_score')})")
    for q in enriched[:5]:
        print(f"    [{q['match_score']}] {q['company']} — {q['role']} ({q['source']})")

    # 6. Apply
    print("\n[6/6] Apply phase...")
    if args.apply:
        if cfg.get("apply",{}).get("auto_approve", False) or args.auto_approve or cfg.get("apply",{}).get("dry_run", True):
            should_auto = args.auto_approve or cfg.get("apply",{}).get("auto_approve", False) or cfg.get("apply",{}).get("dry_run", True)
            if should_auto:
                print("  auto-applying (dry-run)" if cfg.get("apply",{}).get("dry_run") else "  auto-applying live")
                results = apply_batch(scored, profile, limit=args.max_apply)
                print(f"  applied {len(results)} jobs")
                for r in results[:3]:
                    print(f"    -> {r['job'].company} {r['job'].role} : {r['status']}")
            else:
                print("  approval required — jobs queued, run with --auto-approve to submit or approve via dashboard")
        else:
            print("  queued only (need approval)")
    else:
        print("  --apply not set, stopping at queue (use --apply to submit)")

    stats = get_stats()
    print(f"\nTracker: {stats}")
    print("\nDone. Outputs:")
    print("  jobs/jobs.csv, output/ranked_jobs.xlsx, output/approval_queue.json")
    print("  output/tailored/*, output/receipts/*, output/applications.csv")
    print("  Dashboard: python -m src.dashboard.app  (http://localhost:8000)")
    print("="*70)

def main():
    parser = argparse.ArgumentParser(description="AI Job Agent — Autonomous pipeline (works for any role)")
    parser.add_argument("--once", action="store_true", help="run single cycle (default)")
    parser.add_argument("--collect-only", action="store_true", help="only collect jobs")
    parser.add_argument("--skip-collect", action="store_true", help="skip collect, use existing csv")
    parser.add_argument("--tailor-top", type=int, default=8, help="how many top jobs to tailor")
    parser.add_argument("--max-per-source", type=int, default=12)
    parser.add_argument("--max-total", type=int, default=80)
    parser.add_argument("--max-apply", type=int, default=25)
    parser.add_argument("--apply", action="store_true", help="actually apply (or dry-run apply)")
    parser.add_argument("--auto-approve", action="store_true", help="skip approval queue")
    parser.add_argument("--dry-run", action="store_true", help="force dry_run true for this run")
    parser.add_argument("--live", action="store_true", help="force live apply (dry_run false)")
    parser.add_argument("--no-threads", action="store_true")
    parser.add_argument("--watch", type=int, default=0, help="watch mode: re-run every N seconds (0=once)")
    args = parser.parse_args()

    cfg = get_settings()
    if args.dry_run:
        cfg.setdefault("apply",{})["dry_run"] = True
    if args.live:
        cfg.setdefault("apply",{})["dry_run"] = False
    if args.auto_approve:
        cfg.setdefault("apply",{})["auto_approve"] = True

    if args.collect_only:
        ensure_dirs()
        jobs = collect_jobs(max_per_source=args.max_per_source, max_total=args.max_total, use_threads=not args.no_threads)
        save_jobs_csv(jobs)
        return

    if args.watch and args.watch > 0:
        while True:
            run_once(args)
            print(f"\n[watch] sleeping {args.watch}s ... Ctrl+C to stop")
            time.sleep(args.watch)
    else:
        run_once(args)

if __name__ == "__main__":
    main()
