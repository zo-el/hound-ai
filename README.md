# hound-ai

Intelligent scraping and analysis

A Python tool that analyzes construction-related websites to extract relevant keywords and insights using AI.

## Functionality

###Context:

- The salesforce.csv contains the account and opportunity data.
- The outreach.csv contains the call dispositions.

<!--
- The Account Name field could serve as somewhat of a primary key for all of the data.
1. The structure would be an Account Table with the following fields (account name, city, state, website, # of pipeline opps, last sales activity, last connected call date, Lead Score Reason Description, BDR Next Step, PM Software, Accounting Software, Account Owner)
1. The next table is an Opportunity Table that connects to the Account Table based on the Account Name. It contains the following fields (Opportunity Name, Close Date, Primary Reason for Win/Loss, Reason for Win/Loss - Description, Qualification Notes, Opportunity Owner)
1. The next table is an Outreach Table that also connects to the Account Table based on the Account Name. It contains the following fields (Prospect Name, Date, Call Duration, Call Result, Comments) -->

### Stage 1

- Scrape all websites from the Salesforce Export report and store those in an output file

### Stage 2

- Find accounts that do NOT contain “Closed - Currently Not Interested” dispositions in the last 60 days

### Stage 3

- The we will search for keywords across the fields containing qualitative data
  - (Lead Score Reason Description, BDR Next Step, Reason for Win/Loss - Description, Qualification Notes etc)
  - Keywords we could search for would be related their objections (“price”, “pricing”, “cheap”, “afford”)
  - Keywords expressing potential future interest (“interested”, “call back”, “not ready”)
  - Unresponsive accounts (“ghosted”, “unresponsive”, “not responding”)

## Prerequisites

- Python 3.8+
- Ollama installed and running locally (see [Ollama installation guide](https://github.com/ollama/ollama))

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install requests beautifulsoup4 ollama
```
