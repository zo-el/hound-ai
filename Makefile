
setup:
	pip install requests beautifulsoup4 ollama pandas

stage_1:
	python3 scripts/stage_1_keyword_scraper.py

stage_2:
	python3 scripts/stage_2_account_status.py

stage_3:
	python3 scripts/stage_3_sentiment_analysis.py
