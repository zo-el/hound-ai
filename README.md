# hound-ai
Intelligent scraping and analysis

A Python tool that analyzes construction-related websites to extract relevant keywords and insights using AI.

## Features

- Web scraping with rate limiting and proper headers
- AI-powered content analysis using Ollama/LLaMA2
- Focused extraction of construction-related terminology
- Clean text processing with BeautifulSoup4

## Prerequisites

- Python 3.8+
- Ollama installed and running locally (see [Ollama installation guide](https://github.com/ollama/ollama))

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install requests beautifulsoup4 ollama
```

## Usage

1. Make sure Ollama is running
2. Edit the URL in main.py to target your desired website
3. Run the script:

```bash
python main.py
```

## Configuration

- Adjust the `MODEL_NAME` in main.py to use different Ollama models
- Modify the scraping delay in `scrape_website()` if needed
- Customize the analysis prompt in `analyze_content()`

## Rate Limiting

The tool includes a 1-second delay between requests to be respectful to web servers. Adjust this value based on your needs and the website's terms of service.
