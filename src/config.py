from __future__ import annotations
import os
import pathlib
import yaml
from dotenv import load_dotenv

load_dotenv()

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_yaml(path: pathlib.Path | str) -> dict:
    p = ROOT / path if not str(path).startswith("/") else pathlib.Path(path)
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

SETTINGS_PATH = ROOT / "config" / "settings.yaml"
SOURCES_PATH = ROOT / "config" / "sources.yaml"

_settings_cache = None

def get_settings() -> dict:
    global _settings_cache
    if _settings_cache is not None:
        return _settings_cache
    data = load_yaml(SETTINGS_PATH)
    # overlay env vars
    env_overrides = {}
    if os.getenv("OPENAI_API_KEY"):
        env_overrides["openai_api_key"] = os.getenv("OPENAI_API_KEY")
    # TARGET_ROLES etc
    if os.getenv("TARGET_ROLES"):
        data.setdefault("preferences", {})["target_roles"] = [s.strip() for s in os.getenv("TARGET_ROLES", "").split(",") if s.strip()]
    if os.getenv("MIN_MATCH_SCORE"):
        try:
            data.setdefault("preferences", {})["min_match_score"] = int(os.getenv("MIN_MATCH_SCORE"))
        except: pass
    if os.getenv("DRY_RUN"):
        data.setdefault("apply", {})["dry_run"] = os.getenv("DRY_RUN").lower() in ("1","true","yes")
    if os.getenv("AUTO_APPROVE"):
        data.setdefault("apply", {})["auto_approve"] = os.getenv("AUTO_APPROVE").lower() in ("1","true","yes")
    if os.getenv("MAX_APPLICATIONS_PER_RUN"):
        try:
            data.setdefault("apply", {})["max_applications_per_run"] = int(os.getenv("MAX_APPLICATIONS_PER_RUN"))
        except: pass
    _settings_cache = data
    return data

def get_sources() -> dict:
    return load_yaml(SOURCES_PATH)

def resolve_path(p: str) -> pathlib.Path:
    # resolve relative to ROOT
    path = pathlib.Path(p)
    if not path.is_absolute():
        path = ROOT / path
    return path

def ensure_dirs():
    cfg = get_settings()
    for key in [
        cfg.get("collector", {}).get("output_csv", "jobs/jobs.csv"),
        cfg.get("tailoring", {}).get("output_dir", "output/tailored"),
        cfg.get("apply", {}).get("tracker_path", "output/applications.csv"),
        cfg.get("apply", {}).get("receipts_dir", "output/receipts"),
        "output/ranked_jobs.xlsx",
        "output/job_report.xlsx",
        cfg.get("profile", {}).get("resume_path", "resumes/master_resume.docx"),
    ]:
        pp = resolve_path(key)
        # if it's a file, ensure parent exists
        if pp.suffix:
            pp.parent.mkdir(parents=True, exist_ok=True)
        else:
            pp.mkdir(parents=True, exist_ok=True)
    # also ensure generic output dirs
    (ROOT / "output").mkdir(parents=True, exist_ok=True)
    (ROOT / "jobs").mkdir(parents=True, exist_ok=True)
    (ROOT / "resumes").mkdir(parents=True, exist_ok=True)
