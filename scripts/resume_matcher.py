from docx import Document
import pandas as pd
import os

resume_path = "../resumes/master_resume.docx"
jobs_folder = "../jobs"
output_path = "../output/job_report.xlsx"

required_skills = [
    "python", "java", "sql", "aws", "spark", "pyspark",
    "airflow", "databricks", "snowflake", "kafka",
    "spring boot", "react", "node", "git", "jenkins",
    "docker", "kubernetes", "linux", "rest api"
]

doc = Document(resume_path)

resume_text = ""
for para in doc.paragraphs:
    resume_text += para.text.lower() + " "

results = []

for filename in os.listdir(jobs_folder):
    if filename.endswith(".txt"):
        job_path = os.path.join(jobs_folder, filename)

        with open(job_path, "r", encoding="utf-8") as file:
            job_text = file.read().lower()

        lines = job_text.splitlines()

        company = "Unknown"
        role = "Unknown"

        for line in lines:
            if line.startswith("company:"):
                company = line.replace("company:", "").strip()
            if line.startswith("role:"):
                role = line.replace("role:", "").strip()

        matched_skills = []
        missing_skills = []

        for skill in required_skills:
            if skill in resume_text and skill in job_text:
                matched_skills.append(skill)
            elif skill in job_text and skill not in resume_text:
                missing_skills.append(skill)

        total_relevant_skills = len(matched_skills) + len(missing_skills)

        if total_relevant_skills == 0:
            score = 0
        else:
            score = (len(matched_skills) / total_relevant_skills) * 100

        if score >= 75 and len(matched_skills) >= 5:
            decision = "Strong Match - Apply"
        elif score >= 50 and len(matched_skills) >= 3:
            decision = "Medium Match - Review"
        else:
            decision = "Weak Match - Skip or Tailor Resume"

        results.append({
            "Company": company,
            "Role": role,
            "Job File": filename,
            "Match Score": round(score, 2),
            "Matched Skills": ", ".join(matched_skills),
            "Missing Skills": ", ".join(missing_skills),
            "Decision": decision
        })

df = pd.DataFrame(results)
df = df.sort_values(by="Match Score", ascending=False)
df.to_excel(output_path, index=False)

print("========== ALL JOB MATCH REPORT ==========")
print(df)
print()
print("Report saved to output/job_report.xlsx")