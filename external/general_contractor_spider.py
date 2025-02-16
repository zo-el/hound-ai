import scrapy
from bs4 import BeautifulSoup
import re
import time
import random
import json
import os
import csv
from datetime import datetime

class GeneralContractorSpider(scrapy.Spider):
    name = "general_contractor"
    
    custom_settings = {
        "DOWNLOAD_DELAY": 3,  # Delay between requests
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2  # Limit concurrency per domain
    }

    keywords = [
        "commercial construction", "general contractor", "construction management", "construction services", 
        "project management", "contracting", "construction firm", "building contractor", "developer", 
        "general construction", "contractor services", "professional services", "project developer", 
        "commercial development", "commercial building", "retail construction", "industrial construction", 
        "office space construction", "tenant improvements", "structural engineering", 
        "interior buildouts", "design-build", "pre-construction services", "site development", "ground-up construction", "General Contractors", "Commercial", "Healthcare", "industrial"
    ]
    
    def __init__(self, input_file=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.input_file = input_file
        self.results = []

    def start_requests(self):
        if not self.input_file:
            raise ValueError("No input file provided.")
        
        with open(self.input_file, mode='r') as file:
            reader = csv.reader(file)
            for row in reader:
                url = row[0]
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        time.sleep(random.uniform(1, 5))  # Randomized delay
        soup = BeautifulSoup(response.text, 'html.parser')
        text_blocks = self.extract_text_blocks(soup)
        keyword_matches = self.search_keywords(text_blocks)
        
        result = {
            "url": response.url,
            "matches": {keyword: "Yes" for keyword in keyword_matches} if keyword_matches else "No keywords found"
        }
        self.results.append(result)

    def closed(self, reason):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"processed-urls_{timestamp}.json"
        csv_filename = f"filtered-urls_{timestamp}.csv"
        
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(self.results, f, indent=4)
        
        # Extract URLs with keyword matches
        filtered_urls = [entry["url"] for entry in self.results if entry["matches"] != "No keywords found"]
        
        # Save the filtered URLs to a CSV file
        with open(csv_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["URL"])
            for url in filtered_urls:
                writer.writerow([url])
        
        print(f"Results saved to {json_filename}")
        print(f"Filtered URLs saved to {csv_filename}")
    
    def extract_text_blocks(self, soup):
        text_blocks = []
        for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'span', 'div']):
            text = tag.get_text(strip=True)
            if text and len(text) > 30:
                text_blocks.append(text)
        return text_blocks
    
    def search_keywords(self, text_blocks):
        matches = []
        keyword_regex = re.compile(r'\b(' + '|'.join(self.keywords) + r')\b', re.IGNORECASE)
        for text in text_blocks:
            found_keywords = keyword_regex.findall(text)
            if found_keywords:
                matches.extend(found_keywords)
        return list(set(matches))
