from docx import Document
import pandas as pd

# Read resume
doc = Document("../resumes/master_resume.docx")

resume_text = ""

for para in doc.paragraphs:
    resume_text += para.text.lower() + " "

# Skills to check
skills_master_list = [
    "python",
    "sql",
    "aws",
    "spark",
    "pyspark",
    "airflow",
    "databricks",
    "snowflake",
    "kafka",
    "docker",
    "kubernetes",
    "java",
    "linux",
    "git",
    "jenkins",
    "redshift",
    "s3",
    "glue"
]

# Find skills from resume
resume_skills = []

for skill in skills_master_list:
    if skill in resume_text:
        resume_skills.append(skill)

print("Resume Skills:")
print(resume_skills)
print()

# Read jobs
df = pd.read_csv("../jobs/jobs.csv")

scores = []
matched_skills_list = []
missing_skills_list = []

for _, row in df.iterrows():
    description = str(row["Description"]).lower()

    matched_skills = []
    missing_skills = []

    for skill in skills_master_list:
        if skill in description and skill in resume_skills:
            matched_skills.append(skill)
        elif skill in description and skill not in resume_skills:
            missing_skills.append(skill)

    total_relevant = len(matched_skills) + len(missing_skills)

    if total_relevant == 0:
        score = 0
    else:
        score = (len(matched_skills) / total_relevant) * 100

    scores.append(round(score, 2))
    matched_skills_list.append(", ".join(matched_skills))
    missing_skills_list.append(", ".join(missing_skills))

df["Match Score"] = scores
df["Matched Skills"] = matched_skills_list
df["Missing Skills"] = missing_skills_list

df = df.sort_values(by="Match Score", ascending=False)

df.to_excel("../output/ranked_jobs.xlsx", index=False)

print(df[["Company", "Role", "Match Score", "Matched Skills", "Missing Skills"]])
print()
print("Ranked jobs saved to output/ranked_jobs.xlsx")