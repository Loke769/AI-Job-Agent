import pandas as pd

df = pd.read_excel("../output/ranked_jobs.xlsx")

top_job = df.iloc[0]

company = top_job["Company"]
role = top_job["Role"]
matched_skills = top_job["Matched Skills"]

summary = f"""
Data Engineer with hands-on experience in {matched_skills}.
Experienced in building data pipelines, working with cloud platforms,
processing large datasets, and supporting analytics-driven applications.
Interested in contributing to {company} as a {role}.
"""

print("Generated Resume Summary:")
print(summary)
with open("../output/generated_summary.txt", "w", encoding="utf-8") as file:
    file.write(summary)

print("Summary saved to output/generated_summary.txt")