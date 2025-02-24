# hound-ai

Intelligent scraping and analysis

A Python tool that analyzes construction-related websites to extract relevant keywords and insights using AI.

## Functionality

### Context

- The salesforce.csv contains the account and opportunity data.
- The outreach.csv contains the call dispositions.

### Stage 1

- Scrape all websites from the Salesforce Export report and store those in an output file

### Stage 2

- Find accounts that do NOT contain “Closed - Currently Not Interested” dispositions in the last 60 days

### Stage 3

- Search for keywords across the fields containing qualitative data
  - (Lead Score Reason Description, BDR Next Step, Reason for Win/Loss - Description, Qualification Notes etc)
  - Keywords we could search for would be related their objections (“price”, “pricing”, “cheap”, “afford”)
  - Keywords expressing potential future interest (“interested”, “call back”, “not ready”)
  - Unresponsive accounts (“ghosted”, “unresponsive”, “not responding”)

## Prerequisites

- Python 3.8+
- [for deprecated ai runner]Ollama installed and running locally (see [Ollama installation guide](https://github.com/ollama/ollama))
