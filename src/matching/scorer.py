from __future__ import annotations
import re
from typing import List, Tuple
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..models import Job, ScoredJob
from ..resume_parser import detect_skills
from ..config import get_settings

def skill_score(job_desc: str, resume_skills: List[str], master_list: List[str]):
    low_desc = job_desc.lower()
    # dedup master while preserving order
    seen_master = []
    seen_set = set()
    for s in master_list:
        sl = s.lower()
        if sl not in seen_set:
            seen_set.add(sl)
            seen_master.append(s)
    matched = []
    missing = []
    resume_set = set([s.lower() for s in resume_skills])
    seen_job_skills = set()
    for skill in seen_master:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        if re.search(pattern, low_desc):
            if skill.lower() in seen_job_skills:
                continue
            seen_job_skills.add(skill.lower())
            if skill.lower() in resume_set:
                matched.append(skill)
            else:
                missing.append(skill)
    total = len(matched) + len(missing)
    if total == 0:
        return 0.0, matched, missing
    return (len(matched)/total)*100, matched, missing

def tfidf_similarity(job_desc: str, resume_text: str) -> float:
    if not job_desc.strip() or not resume_text.strip():
        return 0.0
    try:
        vec = TfidfVectorizer(stop_words="english", max_features=2000, ngram_range=(1,2))
        tfidf = vec.fit_transform([resume_text.lower(), job_desc.lower()])
        sim = cosine_similarity(tfidf[0:1], tfidf[1:2])[0][0]
        return float(sim*100)
    except Exception:
        return 0.0

def score_jobs(jobs: List[Job], resume_text: str, resume_skills: List[str]) -> List[ScoredJob]:
    cfg = get_settings()
    mcfg = cfg.get("matching", {})
    master = mcfg.get("skills_master_list", [])
    use_tfidf = mcfg.get("use_tfidf", True)
    tfidf_w = float(mcfg.get("tfidf_weight", 0.4))
    skill_w = float(mcfg.get("skill_weight", 0.6))
    prefs = cfg.get("preferences", {})
    strong = int(prefs.get("strong_match_score", 75))
    minimum = int(prefs.get("min_match_score", 50))

    scored: List[ScoredJob] = []
    for j in jobs:
        s_score, matched, missing = skill_score(j.description, resume_skills, master)
        t_score = tfidf_similarity(j.description, resume_text) if use_tfidf else 0
        if use_tfidf:
            final = round(s_score*skill_w + t_score*tfidf_w, 2)
        else:
            final = round(s_score,2)

        # decision logic
        if final >= strong and len(matched) >= 5:
            decision = "Strong Match - Apply"
            label = "Strong"
        elif final >= minimum and len(matched) >= 3:
            decision = "Medium Match - Review"
            label = "Medium"
        else:
            decision = "Weak Match - Skip or Tailor"
            label = "Weak"

        sj = ScoredJob(
            **j.model_dump(),
            match_score=final,
            matched_skills=matched,
            missing_skills=missing,
            tfidf_score=round(t_score,2),
            decision=decision,
            fit_label=label,
        )
        scored.append(sj)
    # sort descending
    scored.sort(key=lambda x: x.match_score, reverse=True)
    return scored

def jobs_to_dataframe(scored: List[ScoredJob]) -> pd.DataFrame:
    rows = []
    for s in scored:
        rows.append({
            "Company": s.company,
            "Role": s.role,
            "Location": s.location,
            "URL": s.url,
            "Description": s.description,
            "Source": s.source,
            "Match Score": s.match_score,
            "Matched Skills": ", ".join(s.matched_skills),
            "Missing Skills": ", ".join(s.missing_skills),
            "TFIDF Score": s.tfidf_score,
            "Decision": s.decision,
            "Fit": s.fit_label,
        })
    return pd.DataFrame(rows)

def save_ranked(scored: List[ScoredJob], xlsx_path="output/ranked_jobs.xlsx", csv_path="output/ranked_jobs.csv"):
    from ..config import resolve_path, ensure_dirs
    ensure_dirs()
    df = jobs_to_dataframe(scored)
    xp = resolve_path(xlsx_path)
    xp.parent.mkdir(parents=True, exist_ok=True)
    cp = resolve_path(csv_path)
    # excel with formatting
    with pd.ExcelWriter(xp, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Ranked Jobs")
        ws = writer.sheets["Ranked Jobs"]
        # auto width
        for col in ws.columns:
            max_len = max((len(str(c.value)) if c.value else 0) for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len+2, 40)
    df.to_csv(cp, index=False)
    print(f"[matching] saved ranked {len(df)} jobs to {xp} and {cp}")
    return xp, df

# helpers for legacy scripts that load csv
def load_jobs_from_csv(path="jobs/jobs.csv") -> List[Job]:
    from ..config import resolve_path
    import hashlib, re
    p = resolve_path(path)
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p).fillna("")
        jobs = []
        for _, row in df.iterrows():
            url = str(row.get("URL",""))
            raw_id = str(row.get("ID","") or url or row.get("Url",""))
            # sanitize id: hash url if it looks like url
            if raw_id.startswith("http") or "/" in raw_id or len(raw_id) > 30:
                raw_id = hashlib.md5(url.encode()).hexdigest()[:12] if url else raw_id[:12]
            # also clean
            raw_id = re.sub(r"[^a-zA-Z0-9]+","_", raw_id)[:16] or hashlib.md5(url.encode()).hexdigest()[:8]
            jobs.append(Job(
                id=raw_id,
                company=str(row.get("Company","Unknown")),
                role=str(row.get("Role","Unknown")),
                location=str(row.get("Location","Remote")),
                url=url,
                description=str(row.get("Description","")),
                source=str(row.get("Source","csv")),
                raw={},
            ))
        return jobs
    except Exception as e:
        print(f"load csv failed: {e}")
        return []
