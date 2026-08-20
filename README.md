# AI Job Agent — Autonomous Application Agent

An end-to-end, open-source job application agent that **watches company career pages, scores fit, tailors your resume and cover letter per role, and auto-applies** — with human approval.

> **What it does:** Monitors company career sites directly (Greenhouse, Lever, Ashby, Workday + 15+ ATSes), scores each posting against your resume, generates a per-role tailored resume and cover letter (with a diff view), queues it for your approval, then submits through the real ATS and saves a receipt. Runs locally, no vendor lock-in.

**Not affiliated with any commercial auto-apply service.** Built as an independent, self-hosted alternative with similar workflow — you own your data, prompts, and submissions.

---

## ✨ What it does

1. **Collect** — Polls Greenhouse `/boards-api`, Lever `api.lever.co`, Ashby `api.ashbyhq.com` for thousands of career pages (starter list in `config/sources.yaml`, scale to as many companies as you want). Offline? Uses realistic demo jobs so the pipeline always works for testing.
2. **Parse** — Reads your `resumes/master_resume.docx` (or `resumes/profile.yaml`), extracts skills. Supports `.docx/.pdf/.txt` for any profession (engineering, data, product, design, marketing, etc.).
3. **Score** — Hybrid **skill + TF-IDF** (skill weight 60% / TF-IDF 40%). Ranks, labels Strong/Medium/Weak, threshold-driven. Works for any role — scoring is generic, not hard-coded to one job family.
4. **Tailor** — Per-role resume + cover letter. Uses **OpenAI (or any LLM) if `OPENAI_API_KEY` set**, otherwise a deterministic template that foregrounds matched keywords and keeps it honest (no fake experience). Generates **diff view** for human review.
5. **Queue** — Approval queue at `output/approval_queue.json` — review every change before it ships.
6. **Apply** — ATS auto-apply via **Playwright** adapters for Greenhouse/Lever/Workday + generic fallback. Default `dry_run=true` (safe: creates receipts without spamming). Set `dry_run=false` + `--live` to really submit.
7. **Track** — `output/applications.csv` + `output/receipts/*.json/.html` per submission (fields filled, answers, timestamp, disclosure). Dashboard at `http://localhost:8000`.

Works for **every role**: Software Engineer, Data Engineer, Data Scientist, Product Manager, Designer, Marketing, etc. — just set `target_roles` in config or via env var and provide any resume. The matcher is role-agnostic.

---

## 🚀 Quickstart (end-to-end in 30 seconds)

```bash
# 1. Install (Python 3.10+ recommended)
pip install -r requirements.txt
# or with venv:
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# 2. (optional) Add your resume
#    Put your real resume at resumes/master_resume.docx
#    If missing, a demo resume is auto-created.
#    You can also edit resumes/profile.yaml directly (works for any role).

# 3. (optional) Configure preferences — no API key required
cp .env.example .env
# edit .env — set TARGET_ROLES, OPENAI_API_KEY, etc — or edit config/settings.yaml

# 4. Run the full pipeline (collect → score → tailor → queue → dry-apply)
python -m src.pipeline --apply
#    or
python run.py --apply

# 5. Open the dashboard (approval queue, diffs, tracker)
python app.py
# -> http://localhost:8000
```

### Run for any role (not just Data Engineer)
```bash
# Example: Software Engineer + Product roles
TARGET_ROLES="Software Engineer, Backend Engineer, Product Manager" python -m src.pipeline --apply

# Or edit config/settings.yaml:
# preferences:
#   target_roles:
#     - "Software Engineer"
#     - "Product Manager"
#     - "UX Designer"

# Example: keep your resume generic, the scorer adapts automatically
```

---

## 💰 Do I need a subscription, AI key, or money?

**No. You can run everything for free.**

| Feature | Free tier | Paid (optional) |
|---|---|---|
| **Collect + Score + Queue + Dry-run Apply** | ✅ Works 100% offline, no key, no cost | — |
| **Template tailoring + diff view** | ✅ Deterministic local templates, no AI needed | — |
| **Dashboard + tracker + receipts** | ✅ Included | — |
| **LLM-powered tailoring** | Optional — set `OPENAI_API_KEY` for higher quality rewrites | ~$0.002–$0.01 per job with `gpt-4o-mini` / `gpt-4o`. 100 tailored jobs ≈ $0.30–$1. You can also use any OpenAI-compatible endpoint or skip entirely. |
| **Real ATS submission** | ✅ Playwright is free; you run it on your machine | No SaaS fee. You only pay for your own OpenAI usage if you enable it. |

**No subscription, no vendor lock-in.** The code is MIT. The default `dry_run=true` generates receipts locally without actually submitting — so you can test end-to-end at zero cost. Only when you set `dry_run: false` and `--live` does it navigate ATS sites (and you still approve each one by default).

---

## 🔧 CLI

```bash
# Collect only (populate jobs/jobs.csv from live boards)
python -m src.pipeline --collect-only
python scripts/real_job_collector.py

# Score + rank (re-creates output/ranked_jobs.xlsx)
python -m src.pipeline --skip-collect
python scripts/job_ranker.py

# Tailor top job (resume + cover + diff)
python scripts/openai_resume_tailor.py

# Full pipeline variations
python -m src.pipeline --apply              # dry-run apply (safe, generates receipts)
python -m src.pipeline --apply --auto-approve
python -m src.pipeline --apply --live --auto-approve   # ⚠️ real Playwright submit (use carefully)
python -m src.pipeline --watch 300          # watch mode: re-run every 5 min

# Legacy compat (still work)
python scripts/resume_matcher.py            # -> output/job_report.xlsx
python scripts/resume_skills.py
python scripts/resume_summary_generator.py
python scripts/chatgpt_prompt_generator.py  # -> output/chatgpt_prompt.txt

# Filter by role at runtime
TARGET_ROLES="Data Analyst, Marketing Manager" python -m src.pipeline --apply
MIN_MATCH_SCORE=40 python -m src.pipeline --apply
```

---

## ⚙️ Configuration

- `config/settings.yaml` — all pipeline knobs: target roles/locations, min scores, skills list, tailoring, ATS, tracker paths. **Supports any role** — the `skills_master_list` covers tech, data, product, design, etc. Add your own keywords.
- `config/sources.yaml` — add unlimited company boards per ATS. Example:
  ```yaml
  greenhouse:
    - token: openai
      company: OpenAI
  lever:
    - token: netflix
      company: Netflix
  ```
  Find Greenhouse token = `boards.greenhouse.io/<TOKEN>`, Lever = `jobs.lever.co/<TOKEN>`. Add 10 or 10,000 companies.
- `.env` — overrides settings at runtime (`OPENAI_API_KEY`, `DRY_RUN`, `AUTO_APPROVE`, `TARGET_ROLES`, etc).
- `resumes/profile.yaml` — declarative profile fallback (name, email, skills, links). Auto-generated if you have no docx. Works for any profession.

---

## 📂 Project Structure

```
AI-Job-Agent
├── config/
│   ├── settings.yaml      # pipeline config (thresholds, ATS, skills — role-agnostic)
│   └── sources.yaml       # career-page list (Greenhouse/Lever/Ashby)
├── resumes/
│   ├── master_resume.docx # your resume (auto-created demo if missing)
│   └── profile.yaml       # parsed profile fallback (any role)
├── jobs/
│   ├── jobs.csv           # collected jobs (compat)
│   └── jobs_full.csv      # enriched with source/date
├── output/
│   ├── ranked_jobs.xlsx/csv
│   ├── approval_queue.json  # queue with diffs
│   ├── tailored/            # per-role resume/cover/diff/docx
│   ├── receipts/            # per-application JSON+HTML receipts
│   ├── applications.csv     # tracker
│   └── job_report.xlsx      # legacy report
├── src/
│   ├── config.py
│   ├── models.py
│   ├── resume_parser.py
│   ├── job_collector/       # Greenhouse / Lever / Ashby + aggregator
│   ├── matching/scorer.py   # skill+TF-IDF (generic)
│   ├── tailoring/engine.py  # OpenAI or template + diff (role-agnostic)
│   ├── apply/               # applier + tracker (Playwright)
│   ├── dashboard/app.py     # FastAPI UI
│   └── pipeline.py          # end-to-end orchestrator
├── scripts/                 # thin wrappers (backward compat)
├── extension/               # Chrome toolbar (optional)
├── mcp/                     # CLI / agent adapter (optional)
├── app.py                   # dashboard launcher
└── run.py                   # pipeline launcher
```

---

## 🧠 Scoring

`final = skill_score*0.6 + tfidf*0.4`

- `skill_score` = matched / (matched+missing) *100 where skills are in `skills_master_list` (you can edit it for any industry).
- `tfidf` = cosine similarity resume vs job description (1-2gram, English stopwords) — works for any text, any role.

Thresholds: `min_match_score=50` (queue), `strong_match_score=75`. Lower to 35–40 if you want higher volume for exploratory roles.

---

## ✍️ Tailoring

- If `OPENAI_API_KEY` present → calls `gpt-4o-mini` (or your configured model) with an honest prompt (never invent).
- Else → deterministic template: reorders skills (matched first), injects tailored summary mentioning top matched skills for the target **role**, keeps original experience + adds relevance bullet, generates cover letter (200 words). Works without any AI cost.

Tailoring is **role-agnostic**: the prompt uses `Role: {role}` dynamically, so it adapts to Software Engineer, Product Manager, Designer, etc.

Diff via `difflib.unified_diff` stored in `output/tailored/*_diff.txt` and shown in dashboard.

---

## 🤖 Auto-Apply (ATS)

Adapters in `src/apply/applier.py`:

- **Greenhouse** — clicks Apply, fills name/email/phone, uploads tailored docx, answers open-ended Qs in your voice.
- **Lever** — similar, handles `hostedUrl`/`applyUrl`.
- **Ashby/Workday** — generic Playwright fallback (label/placeholder selector).

Safety: `dry_run=true` default. Only does real navigation when you set `dry_run: false` in settings **and** pass `--live`. Even then, requires `auto_approve=true` or manual dashboard approval — “approve before submit” workflow.

Each apply saves:

- `output/receipts/<company>_<role>_<ts>.json` — fields, answers, timestamp, disclosure
- `output/applications.csv` — tracker

Answers auto-generated for: *Why this company?*, *Tools*, *Authorization*, *Sponsorship*, *Salary*, *Notice period* — role-aware.

---

## 📊 Dashboard

```bash
python app.py  # http://localhost:8000
# or
uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000 --reload
```

Tabs: **Queue** (tailored previews + diff + Approve/Skip), **Ranked**, **Tracker**. Also JSON APIs: `/api/queue`, `/api/ranked`, `/api/stats`. Works via preview proxy when hosted.

---

## 🚀 Deployment Overview

### Option A — Local (fastest, free)
1. Clone, `pip install -r requirements.txt`
2. Add resume to `resumes/` (optional)
3. `python -m src.pipeline --apply && python app.py`
- Good for daily runs, cron, or `--watch 3600`.

### Option B — Docker (portable)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "src.pipeline", "--apply"]
# dashboard: docker run -p 8000:8000 your-image uvicorn src.dashboard.app:app --host 0.0.0.0 --port 8000
```
```bash
docker build -t ai-job-agent .
docker run --env-file .env -v $(pwd)/output:/app/output ai-job-agent
```

### Option C — Free cloud (always-on watching)
- **Render / Railway / Fly.io / Hugging Face Spaces**: push repo, set start command `uvicorn src.dashboard.app:app --host 0.0.0.0 --port $PORT`, add env vars (`OPENAI_API_KEY` optional), mount/persist `output/` if you want history.
- **GitHub Actions (scheduled collect)**: add `.github/workflows/collect.yml` with cron `0 */6 * * *` running `python -m src.pipeline --apply`.
- No paid SaaS required; you pay only if you enable LLM calls, at OpenAI's per-token price.

**Env vars for cloud:**
```
OPENAI_API_KEY=sk-...           # optional
TARGET_ROLES=Software Engineer, Product Manager
MIN_MATCH_SCORE=45
DRY_RUN=true
AUTO_APPROVE=false
```

---

## 🔒 Honesty & Safety

- Never invents employers/dates/tools (enforced in prompt + template).
- Disclosure added to receipts.
- `exclude_companies`, `exclude_keywords`, sponsorship filter in settings.
- Tracker prevents double-apply.
- Respect each site’s ToS; use dry-run while testing.

---

## 🧪 Tests

```bash
python tests/test_pipeline.py          # offline smoke test
python -m src.pipeline --apply         # should create ranked_jobs.xlsx + approval_queue.json + receipts
ls output/
```

---

## 📝 License

MIT — for learning. Use responsibly: only apply with truthful materials and respect site ToS.

## 🙏 Credits

Independent open-source project. Inspired by the general concept of autonomous application agents that watch career pages across multiple ATSes and tailor per role — built from scratch with open tools (Greenhouse/Lever/Ashby public APIs, Playwright, scikit-learn).
