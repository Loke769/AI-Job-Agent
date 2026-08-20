install:
	pip install --break-system-packages -r requirements.txt

collect:
	python -m src.pipeline --collect-only

rank:
	python scripts/job_ranker.py

tailor:
	python scripts/openai_resume_tailor.py

pipeline:
	python -m src.pipeline --apply

dashboard:
	python app.py

test:
	python tests/test_pipeline.py

clean:
	rm -rf output/tailored/* output/receipts/* output/applications.csv

