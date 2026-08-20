from __future__ import annotations
import os
import pathlib
import re
import difflib
import textwrap
from datetime import datetime
from typing import Tuple
import yaml

from ..config import get_settings, resolve_path, ensure_dirs, ROOT
from ..models import ScoredJob, ResumeProfile

# Prompt templates — role-agnostic (works for any profession)
RESUME_TAILOR_PROMPT = """You are an expert resume writer.
Keep it honest: do not invent experience, employers, dates, or tools not in the original resume.
Optimize for ATS keyword matching for the target role.

Original resume:
{resume_text}

Target job: {role} at {company}
Job description:
{job_desc}

Matched skills: {matched}
Missing skills (do not fake but show adjacent honest phrasing if possible): {missing}

Tasks:
1. Rewrite the SUMMARY to be 2-3 sentences tailored to this role, mentioning top 3 matched skills naturally.
2. Rewrite EXPERIENCE bullet points to foreground results relevant to this job (keep true facts, reorder, quantify).
3. Ensure SKILLS section surfaces matched skills first.
Return ONLY the tailored resume text (no commentary).
"""

COVER_LETTER_PROMPT = """You are writing a concise, human cover letter.

Candidate: {name} — {email} — {location}
Resume summary: {resume_summary}
Job: {role} at {company}
Job description: {job_desc}
Matched skills: {matched}

Write a 180-220 word cover letter:
- 3 paragraphs, professional but warm
- Show why fit, mention 2-3 concrete achievements relevant to job
- Do not hallucinate employers not in resume
- Close with call to action
"""

def call_openai(prompt: str, system: str = "You are a helpful assistant.") -> str | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=key)
        model = get_settings().get("tailoring", {}).get("model", "gpt-4o-mini")
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"system","content":system},{"role":"user","content":prompt}],
            temperature=0.4,
            max_tokens=1200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[tailoring] OpenAI call failed: {e}")
        return None

def template_tailor_resume(profile: ResumeProfile, job: ScoredJob) -> str:
    matched = ", ".join(job.matched_skills) if job.matched_skills else "core professional skills"
    missing_note = ", ".join(job.missing_skills[:4]) if job.missing_skills else "none"
    header = f"""{profile.name}
{profile.email} | {profile.phone} | {profile.location}
{profile.linkedin} | {profile.github}

"""
    summary = textwrap.dedent(f"""
    SUMMARY
    {job.role} candidate with experience in {matched}. Proven in delivering impact,
    collaborating across teams, and improving systems. Excited to contribute to {job.company} as {job.role},
    bringing focus on {matched} and continuous growth in {missing_note if missing_note!='none' else 'modern stack'}.
    """).strip()

    all_skills = profile.skills
    ordered = job.matched_skills + [s for s in all_skills if s not in job.matched_skills]
    skills_section = "SKILLS\n" + ", ".join(ordered[:18])

    exp = profile.raw_text
    relevance_bullet = f"- Tailored relevance for {job.role}: experience with {matched} aligned to job's focus on {job.description[:120]}..."
    tailored = header + summary + "\n\n" + skills_section + "\n\nEXPERIENCE\n(Original experience retained; tailored highlights below)\n" + relevance_bullet + "\n\n" + exp[:2000]
    return tailored

def template_cover_letter(profile: ResumeProfile, job: ScoredJob) -> str:
    matched = ", ".join(job.matched_skills[:5]) if job.matched_skills else "relevant skills"
    return textwrap.dedent(f"""
    {profile.name}
    {profile.email} | {profile.phone}
    {datetime.utcnow().strftime('%B %d, %Y')}

    Hiring Manager
    {job.company}

    Dear Hiring Manager,

    I am excited to apply for the {job.role} role at {job.company}. With experience in {matched}, I was drawn to your team's focus on {job.description[:140].strip()}.

    In my recent role I delivered projects that improved efficiency and quality — outcomes directly relevant to your need for {matched}. I care deeply about collaboration, quality, and enabling teams with reliable solutions.

    I would love to bring my background in {matched} and collaborative approach to {job.company}. Thank you for considering my application — I welcome the chance to discuss how I can contribute to your goals.

    Sincerely,
    {profile.name}
    """).strip()

def diff_view(original: str, tailored: str) -> str:
    diff = difflib.unified_diff(original.splitlines(), tailored.splitlines(), fromfile="original", tofile="tailored", lineterm="", n=3)
    return "\n".join(list(diff)[:120])

def tailor_for_job(profile: ResumeProfile, job: ScoredJob) -> Tuple[str, str, str]:
    resume_text = None
    cover = None
    if os.getenv("OPENAI_API_KEY"):
        p1 = RESUME_TAILOR_PROMPT.format(resume_text=profile.raw_text[:4000], role=job.role, company=job.company, job_desc=job.description[:3000], matched=", ".join(job.matched_skills), missing=", ".join(job.missing_skills))
        resume_text = call_openai(p1, "You are an expert resume writer. Be honest and concise.")
        p2 = COVER_LETTER_PROMPT.format(name=profile.name, email=profile.email, location=profile.location, resume_summary=profile.summary[:600], role=job.role, company=job.company, job_desc=job.description[:2500], matched=", ".join(job.matched_skills))
        cover = call_openai(p2, "You are an expert cover letter writer.")
    if not resume_text:
        resume_text = template_tailor_resume(profile, job)
    if not cover:
        cover = template_cover_letter(profile, job)
    diff = diff_view(profile.raw_text[:3000], resume_text[:3000])
    return resume_text, cover, diff

def save_tailored(job: ScoredJob, resume_text: str, cover_letter: str, diff_text: str):
    cfg = get_settings()
    out_dir = resolve_path(cfg.get("tailoring", {}).get("output_dir", "output/tailored"))
    ensure_dirs()
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_company = re.sub(r"[^a-zA-Z0-9]+","_", job.company)[:30]
    safe_role = re.sub(r"[^a-zA-Z0-9]+","_", job.role)[:30]
    safe_id = re.sub(r"[^a-zA-Z0-9]+","_", job.id)[:12]
    if not safe_id or len(safe_id) < 3:
        import hashlib
        safe_id = hashlib.md5(job.url.encode()).hexdigest()[:8]
    base = f"{safe_company}__{safe_role}__{safe_id}"
    resume_path = out_dir / f"{base}_resume.txt"
    cover_path = out_dir / f"{base}_cover.txt"
    diff_path = out_dir / f"{base}_diff.txt"
    docx_path = out_dir / f"{base}_resume.docx"
    resume_path.write_text(resume_text, encoding="utf-8")
    cover_path.write_text(cover_letter, encoding="utf-8")
    diff_path.write_text(diff_text, encoding="utf-8")
    try:
        from docx import Document
        from docx.shared import Pt
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'Calibri'
        style.font.size = Pt(10)
        for line in resume_text.splitlines():
            doc.add_paragraph(line)
        doc.save(str(docx_path))
    except Exception as e:
        print(f"docx tailoring save failed: {e}")
        docx_path = resume_path
    html_path = out_dir / f"{base}.html"
    html_path.write_text(f"<h2>{job.role} at {job.company}</h2><p>Score {job.match_score}</p><pre>{resume_text[:3000]}</pre><hr><pre>{cover_letter[:3000]}</pre>", encoding="utf-8")
    return str(resume_path), str(cover_path), str(diff_path), str(docx_path)

def generate_prompt_file(job: ScoredJob, profile: ResumeProfile):
    out = resolve_path("output/chatgpt_prompt.txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    prompt = f"""
You are my resume tailoring assistant.

Target Role: {job.role}
Company: {job.company}
Location: {job.location}
URL: {job.url}

Job Description:
{job.description}

Matched Skills:
{', '.join(job.matched_skills)}

Missing Skills:
{', '.join(job.missing_skills)}

Candidate profile:
{profile.raw_text[:3000]}

Task:
1. Create a strong tailored resume summary.
2. Create 5 resume bullet points for this role.
3. Create a short cover letter.
4. Keep it honest. Do not add fake experience.
5. Optimize for {job.role} roles.
"""
    out.write_text(prompt.strip(), encoding="utf-8")
    return out
