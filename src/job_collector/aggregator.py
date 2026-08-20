from __future__ import annotations
import random
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

from ..config import get_settings, get_sources, resolve_path, ensure_dirs
from ..models import Job
from .greenhouse import GreenhouseCollector
from .lever import LeverCollector
from .ashby import AshbyCollector

# Demo fallback — diverse roles so the pipeline demonstrates for every profession
DEMO_JOBS = [
    {"Company": "Snowflake", "Role": "Data Engineer", "Location": "Remote, USA", "URL": "https://boards.greenhouse.io/snowflake/jobs/123", "Description": "We need Python, SQL, AWS, Spark, Snowflake, Kafka, Airflow, dbt, Docker. Build scalable ELT pipelines on AWS S3 and Snowflake.", "Source": "greenhouse"},
    {"Company": "Stripe", "Role": "Software Engineer (Backend)", "Location": "San Francisco, CA", "URL": "https://boards.greenhouse.io/stripe/jobs/789", "Description": "Build backend services with Python, Java, AWS, Kubernetes, Docker, CI/CD, SQL. Own APIs and data pipelines for payments.", "Source": "greenhouse"},
    {"Company": "Figma", "Role": "Product Designer", "Location": "Remote", "URL": "https://boards.greenhouse.io/figma/jobs/321", "Description": "We seek Figma, UX, UI, agile, communication, leadership. Craft design systems and collaborate with engineering and product.", "Source": "greenhouse"},
    {"Company": "Notion", "Role": "Product Manager", "Location": "New York, NY", "URL": "https://jobs.ashbyhq.com/notion/jkl", "Description": "Product management, agile, scrum, communication, leadership, UX. Drive roadmap for collaborative tools.", "Source": "ashby"},
    {"Company": "Databricks", "Role": "Senior Data Engineer", "Location": "San Francisco, CA", "URL": "https://boards.greenhouse.io/databricks/jobs/456", "Description": "Looking for PySpark, Spark, Databricks, AWS, Terraform, Delta Lake, Airflow. Optimize large-scale data platform.", "Source": "greenhouse"},
    {"Company": "Linear", "Role": "Frontend Engineer", "Location": "Remote", "URL": "https://jobs.ashbyhq.com/linear/xyz", "Description": "React, TypeScript, JavaScript, Node, CI/CD, Git. Build fast, delightful interfaces.", "Source": "ashby"},
    {"Company": "Shopify", "Role": "Marketing Manager", "Location": "Remote, Canada", "URL": "https://jobs.lever.co/shopify/def", "Description": "Marketing, communication, leadership, agile, SQL, tableau. Own growth and analytics for e-commerce.", "Source": "lever"},
    {"Company": "Netflix", "Role": "Data Scientist", "Location": "Los Gatos, CA", "URL": "https://jobs.lever.co/netflix/abc", "Description": "Python, SQL, bigquery, tableau, looker, communication. Build models for personalization and streaming analytics.", "Source": "lever"},
]

def build_collectors(max_per_source: int) -> List:
    sources = get_sources()
    collectors = []
    for entry in sources.get("greenhouse", []):
        collectors.append(GreenhouseCollector(entry["token"], entry["company"], max_jobs=max_per_source))
    for entry in sources.get("lever", []):
        collectors.append(LeverCollector(entry["token"], entry["company"], max_jobs=max_per_source))
    for entry in sources.get("ashby", []):
        collectors.append(AshbyCollector(entry["token"], entry["company"], max_jobs=max_per_source))
    return collectors

def collect_jobs(max_per_source: int = None, max_total: int = 200, use_threads: bool = True, include_demo: bool = True) -> List[Job]:
    cfg = get_settings()
    max_per_source = max_per_source or cfg.get("collector", {}).get("max_jobs_per_source", 12)
    collectors = build_collectors(max_per_source)
    all_jobs: List[Job] = []
    prefs = cfg.get("preferences", {})
    exclude_companies = set([c.lower() for c in prefs.get("exclude_companies",[])])
    exclude_keywords = [k.lower() for k in prefs.get("exclude_keywords",[])]

    if collectors:
        if use_threads:
            with ThreadPoolExecutor(max_workers=8) as ex:
                fut_to_col = {ex.submit(c.fetch): c for c in collectors}
                for fut in as_completed(fut_to_col):
                    col = fut_to_col[fut]
                    try:
                        jobs = fut.result()
                        all_jobs.extend(jobs)
                        print(f"[collector] {col.ats_name}:{col.token} -> {len(jobs)} jobs")
                    except Exception as e:
                        print(f"[collector] {col} failed: {e}")
                    time.sleep(0.05)
        else:
            for c in collectors:
                try:
                    jobs = c.fetch()
                    all_jobs.extend(jobs)
                    print(f"[collector] {c.ats_name}:{c.token} -> {len(jobs)}")
                except Exception as e:
                    print(e)

    if len(all_jobs) < 8 and include_demo:
        print(f"[collector] only {len(all_jobs)} live jobs — injecting demo set (diverse roles) for offline demo")
        for row in DEMO_JOBS:
            all_jobs.append(Job(
                id=row["URL"].split("/")[-1],
                company=row["Company"],
                role=row["Role"],
                location=row["Location"],
                url=row["URL"],
                description=row["Description"],
                source=row["Source"],
                raw={},
            ))

    seen = set()
    deduped: List[Job] = []
    for j in all_jobs:
        if j.url not in seen:
            seen.add(j.url)
            deduped.append(j)
    filtered: List[Job] = []
    for j in deduped:
        if j.company.lower() in exclude_companies:
            continue
        if any(kw in j.role.lower() for kw in exclude_keywords):
            continue
        filtered.append(j)
        if len(filtered) >= max_total:
            break

    random.seed(42)
    random.shuffle(filtered)
    print(f"[collector] total unique jobs after filter: {len(filtered)} (from {len(all_jobs)} raw)")
    return filtered[:max_total]

def save_jobs_csv(jobs: List[Job], path: str = None):
    cfg = get_settings()
    out = path or cfg.get("collector", {}).get("output_csv", "jobs/jobs.csv")
    p = resolve_path(out)
    ensure_dirs()
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = [j.to_csv_row() for j in jobs]
    if not rows:
        pd.DataFrame(columns=["Company","Role","Location","URL","Description","Source","DatePosted"]).to_csv(p, index=False)
        return p
    df = pd.DataFrame(rows)
    df_compat = df[["Company","Role","Location","URL","Description"]]
    df_compat.to_csv(p, index=False)
    df.to_csv(str(p).replace(".csv","_full.csv"), index=False)
    print(f"[collector] saved {len(df)} jobs to {p}")
    return p

if __name__ == "__main__":
    ensure_dirs()
    jobs = collect_jobs()
    save_jobs_csv(jobs)
