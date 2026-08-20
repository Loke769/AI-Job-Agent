# Deployment & Cost Guide — AI Job Agent

This guide answers: **Do I need a subscription/AI/money? How do I run and deploy?**

## TL;DR

- **No subscription needed.** Clone, `pip install -r requirements.txt`, `python -m src.pipeline --apply` — works 100% offline for free.
- **No AI key required.** Without an API key the pipeline uses local templates (deterministic, honest, free). Add `OPENAI_API_KEY` only if you want LLM-powered rewrites (~$0.002–$0.01 per job).
- **Deploy anywhere**: local laptop, Docker, or free cloud (Render/Railway/Fly/Hugging Face). No vendor lock-in.

---

## 1. What costs money (and what doesn't)

| Component | Free (default) | Optional Paid |
|---|---|---|
| **Job collection** (Greenhouse/Lever/Ashby public APIs) | ✅ Free — public JSON, no auth | — |
| **Scoring & ranking** (skill + TF-IDF) | ✅ Free — local scikit-learn | — |
| **Tailoring** — template mode | ✅ Free — local deterministic templates with diff view | — |
| **Tailoring** — LLM mode | — | `OPENAI_API_KEY` → `gpt-4o-mini` ≈ $0.002–$0.01 per job. 100 jobs ≈ $0.30–$1. Also works with any OpenAI-compatible endpoint (Groq, Together, local Ollama with small code change). |
| **Auto-apply** (Playwright) | ✅ Free — runs on your machine | — |
| **Dashboard + tracker** | ✅ Free — FastAPI | — |
| **Hosting** | ✅ Free tier on Render/Railway/Fly (256–512MB RAM enough) | Pay only if you exceed free tier |

**You never need to “put money” to try end-to-end:**
```bash
python -m src.pipeline --apply   # dry_run=true by default → generates receipts, no real submits, no cost
ls output/receipts/              # JSON+HTML receipts
ls output/tailored/              # per-role resumes + diffs
```

Only when you set `dry_run: false` + `--live` does it navigate ATS sites live (and even then, `auto_approve: false` waits for your click).

---

## 2. How to run (for any role)

### A. Local — 3 steps (recommended to start)

1. **Install**
   ```bash
   git clone https://github.com/Loke769/AI-Job-Agent
   cd AI-Job-Agent
   python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Add your resume (any profession)**
   - Put any resume at `resumes/master_resume.docx` (PDF/TXT also works), **or**
   - Edit `resumes/profile.yaml` directly:
     ```yaml
     name: Your Name
     email: you@example.com
     skills: [python, react, product management, figma, ...]  # any skills
     raw_text: |
       Your full resume text here...
     ```
   - If missing, a demo is auto-created — pipeline still runs for testing.

3. **Configure roles (no code change)**
   ```bash
   # Option 1: env var (works for any role)
   TARGET_ROLES="Software Engineer, Product Manager, Marketing Manager" python -m src.pipeline --apply

   # Option 2: edit config/settings.yaml
   # preferences:
   #   target_roles: ["Frontend Engineer", "UX Designer", "Data Analyst"]

   # Option 3: .env file
   cp .env.example .env   # edit TARGET_ROLES there
   ```

4. **Run**
   ```bash
   python -m src.pipeline --apply   # collect → score → tailor → queue → dry-apply
   python app.py                    # dashboard http://localhost:8000
   ```

**Works for every role** because:
- `skills_master_list` in `config/settings.yaml` covers tech/data/product/design/business — add your own keywords.
- Scoring is hybrid TF-IDF (generic text similarity) + skill overlap — no hard-coded job family.
- Tailoring prompt uses `Role: {role}` dynamically, so it adapts to “Software Engineer” or “Marketing Manager”.

### B. Test each helper

```bash
python scripts/real_job_collector.py      # fetch live boards → jobs/jobs.csv
python scripts/job_ranker.py              # score → output/ranked_jobs.xlsx
python scripts/openai_resume_tailor.py    # tailor top job (LLM or template)
python tests/test_pipeline.py             # offline smoke test
```

---

## 3. How to deploy (pick one)

### Option 1: Docker (portable, works anywhere)

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "src.dashboard.app:app", "--host", "0.0.0.0", "--port", "8000"]
```
```bash
docker build -t ai-job-agent .
docker run --env-file .env -p 8000:8000 -v $(pwd)/output:/app/output ai-job-agent
# pipeline: docker run --env-file .env ai-job-agent python -m src.pipeline --apply
```

### Option 2: Free cloud — always-on watcher

**Render / Railway / Fly.io / Hugging Face Spaces:**
- Push repo to GitHub.
- Create new Web Service → connect repo.
- Start command: `uvicorn src.dashboard.app:app --host 0.0.0.0 --port $PORT`
- Add env vars in dashboard: `OPENAI_API_KEY` (optional), `TARGET_ROLES`, `DRY_RUN=true`, etc.
- Mount `output/` as persistent disk if you want history across restarts.

**GitHub Actions (scheduled):**
```yaml
# .github/workflows/pipeline.yml
on:
  schedule: [{ cron: "0 */6 * * *" }]  # every 6 hours
  workflow_dispatch: {}
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - run: python -m src.pipeline --apply
      - uses: actions/upload-artifact@v4
        with: { name: output, path: output/ }
```

### Option 3: VPS / Raspberry Pi / your laptop cron

```bash
crontab -e
# every hour, watch & apply (dry-run)
0 * * * * cd /home/you/AI-Job-Agent && /home/you/.venv/bin/python -m src.pipeline --apply >> output/cron.log 2>&1
```

---

## 4. Enabling AI tailoring (optional)

**Without key:** template mode → reorders skills, injects role-relevant summary, keeps honest, generates diff. Good for testing.

**With key (better quality):**
1. Get key at https://platform.openai.com/api-keys
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-proj-...
   OPENAI_MODEL=gpt-4o-mini
   ```
3. Cost: `gpt-4o-mini` ~ $0.15 / 1M input tokens, $0.60 / 1M output → ~ $0.003 per tailored resume+cover. Set `MAX_APPLICATIONS_PER_RUN=10` to cap spend.
4. Alternative: use Groq/Together/local Ollama — change `src/tailoring/engine.py` `OpenAI(..., base_url="...")`.

No subscription to this repo — you only pay OpenAI directly, if you choose to.

---

## 5. Real ATS submission safety

- Default `apply.dry_run: true` — **never hits “Submit”**, just creates receipts.
- To go live:
  ```bash
  # in config/settings.yaml or .env
  DRY_RUN=false
  AUTO_APPROVE=false   # requires dashboard click per job (safer)
  python -m src.pipeline --apply --live
  ```
- Tracker `output/applications.csv` prevents double-apply.
- Always respect each company’s ToS; use dry-run while tuning.

---

## 6. FAQ

**Q: Does it work for non-tech roles?**  
Yes. Add your target titles to `target_roles`, add role-specific keywords to `skills_master_list` (e.g., `figma, ux, salesforce, seo`), and provide a matching resume. TF-IDF handles generic text even without a skill hit.

**Q: Do I need to pay for Greenhouse/Lever/Ashby?**  
No — the collector uses their public job board JSON (same as career site). No API key.

**Q: How do I add more companies?**  
Edit `config/sources.yaml` — add `token: companyname` under `greenhouse`/`lever`/`ashby`. Find token from the URL: `boards.greenhouse.io/<token>`, `jobs.lever.co/<token>`. Add 10 or 10,000.

**Q: How to deploy the Chrome extension?**  
Load unpacked at `chrome://extensions` → Developer mode → Load unpacked → select `extension/` folder. Injects a toolbar on ATS pages.

**Q: Can I run without Python?**  
Use Docker — no Python install needed beyond Docker Desktop.

---

## 7. Quick checklist before you push to cloud

- [ ] `resumes/profile.yaml` or `master_resume.docx` present
- [ ] `config/settings.yaml` — `target_roles`, `target_locations`, `min_match_score` set
- [ ] `.env` — `OPENAI_API_KEY` only if you want LLM mode
- [ ] Test locally: `python -m src.pipeline --apply && ls output/`
- [ ] Choose deploy target, set same env vars there, expose port 8000 for dashboard

MIT licensed — self-hosted, you own the data.
