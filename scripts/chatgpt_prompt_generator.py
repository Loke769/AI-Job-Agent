import pandas as pd

df = pd.read_excel("../output/ranked_jobs.xlsx")

top_job = df.iloc[0]

company = top_job["Company"]
role = top_job["Role"]
description = top_job["Description"]
matched_skills = top_job["Matched Skills"]
missing_skills = top_job["Missing Skills"]

prompt = f"""
You are my resume tailoring assistant.

Target Role: {role}
Company: {company}

Job Description:
{description}

Matched Skills:
{matched_skills}

Missing Skills:
{missing_skills}

Task:
1. Create a strong tailored resume summary.
2. Create 5 resume bullet points for this role.
3. Create a short cover letter.
4. Keep it honest. Do not add fake experience.
5. Optimize for Data Engineer roles.
"""

with open("../output/chatgpt_prompt.txt", "w", encoding="utf-8") as file:
    file.write(prompt)

print("ChatGPT prompt saved to output/chatgpt_prompt.txt")