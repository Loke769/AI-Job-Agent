from docx import Document

doc = Document("../resumes/master_resume.docx")

resume_text = ""

for para in doc.paragraphs:
    resume_text += para.text.lower() + " "

skills = [
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
    "java"
]

found_skills = []

for skill in skills:
    if skill in resume_text:
        found_skills.append(skill)

print("Skills found in resume:")
print(found_skills)