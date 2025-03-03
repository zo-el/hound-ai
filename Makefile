analyze_keywords:
	python3 scripts/analyze_keywords.py

setup:
	pip install requests beautifulsoup4 ollama pandas tqdm openpyxl

stage_1:
	python3 scripts/stage_1_keyword_scraper.py

stage_2:
	python3 scripts/stage_2_account_status.py

stage_3:
	python3 scripts/stage_3_sentiment_analysis.py

stage_4:
	python3 scripts/stage_4_excel_formatter.py

calculate_scores:
	python3 scripts/calculate_company_scores.py

all: stage_1 stage_2 stage_3 stage_4 analyze_keywords calculate_scores
