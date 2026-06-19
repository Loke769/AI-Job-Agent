import pandas as pd

jobs = [
    {
        "Company": "Sample Company",
        "Role": "Data Engineer",
        "Location": "Remote",
        "URL": "https://example.com",
        "Description": "Python SQL AWS Spark Airflow Databricks Snowflake"
    }
]

df = pd.DataFrame(jobs)

df.to_csv("../jobs/jobs.csv", index=False)

print("Real job collector skeleton created.")
print("jobs/jobs.csv updated.")