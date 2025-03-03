# ## Usage

# 1. Make sure Ollama is running
# 2. Edit the URL in main.py to target your desired website
# 3. Run the script:

# ```bash
# python main.py
# ```

# ## Configuration

# - Adjust the `MODEL_NAME` in main.py to use different Ollama models
# - Modify the scraping delay in `scrape_website()` if needed
# - Customize the analysis prompt in `analyze_content()`

# ## Rate Limiting

# The tool includes a 1-second delay between requests to be respectful to web servers. Adjust this value based on your needs and the website's terms of service.


from bs4 import BeautifulSoup
import requests
import ollama
import time
from typing import Optional, Dict, List, Tuple
import re  # For pattern matching
import html  # For decoding HTML entities
import csv  # Import the csv module
import os
from datetime import datetime
import multiprocessing
from functools import partial
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the model
try:
    client = ollama.Client()
    # Using the latest llama2 model
    MODEL_NAME = "llama3.2"
except Exception as e:
    logger.error(f"Error initializing Ollama: {e}")
    exit(1)

PROMPTS = [
    (
        "Find keywords",
        """
        Analyze the following website content and extract keywords related to construction services. 
        Focus on terms like commercial construction, general contractor, design-build, etc.
        
        Only respond with the found keywords, separated by commas. If no keywords are found, respond with "No relevant keywords found."
        
        Content to analyze:
        {content}
        """
    )
    # (
    #     "Count Keywords", 
    #     """
    #     Count the number of times the keywords appear in website content. 
    #     Keywords:
    #     [
    #         "commercial construction", "general contractor", "construction management", "construction services", 
    #         "project management", "contracting", "construction firm", "building contractor", "developer", 
    #         "general construction", "contractor services", "professional services", "project developer", 
    #         "commercial development", "commercial building", "retail construction", "industrial construction", 
    #         "office space construction", "tenant improvements", "structural engineering", 
    #         "interior buildouts", "design-build", "pre-construction services", "site development", "ground-up construction", "General Contractors", "Commercial", "Healthcare", "industrial"     
    #     ]    
        
    #     - See that the keywords can be in any case.
    #     - Ignore the words from companies blogs or article pages. 
    #     - I want you to be very strict and only count the keywords that I have provided. 
        
    #     While responding, provide the count of each keyword and the specific locations where they appear in the content. 
    #     For example:
    #     commercial construction: 10
    #     Locations: [
    #         - Found in the main page under the image of a building
    #         - Found in the second paragraph of the About Us page
    #     ]
    #     general contractor: 5
    #     Locations: [
    #         - Found in the services section
    #     ]

    #     """
    # ),
    # (
    #     "Proof", 
    #     """
    #     Count the number of times the keywords appear in website content. 
    #     Keywords:
    #     [
    #         "commercial construction", "general contractor", "construction management", "construction services", 
    #         "project management", "contracting", "construction firm", "building contractor", "developer", 
    #         "general construction", "contractor services", "professional services", "project developer", 
    #         "commercial development", "commercial building", "retail construction", "industrial construction", 
    #         "office space construction", "tenant improvements", "structural engineering", 
    #         "interior buildouts", "design-build", "pre-construction services", "site development", "ground-up construction", "General Contractors", "Commercial", "Healthcare", "industrial"     
    #     ]    
        
    #     - See that the keywords can be in any case.
    #     - Ignore the words from companies blogs or article pages. 
    #     - I want you to be very strict and only count the keywords that I have provided. 
        
    #     While responding, provide the exact page and a way to find the keyword. 
    #     For example:
    #     commercial construction: [
    #         - Found on the main page under the image of a building
    #         - In the subtext that is not visible on the page
    #     ]
    #     general contractor: [
    #         - When you click on the About Us page, you will see it in the second paragraph
    #     ]

    #     """
    # ),
    # (
    #     "Keyword Analysis", 
    #     """
    #         Analyze the content for keywords related to commercial general contracting like pre-construction, construction management, design build or design-build, tenant improvements.
    #         Ignore the words from companies blogs or article pages. 
    #         Content:
    #           {content[:4000]}  # Limit content length to avoid token limits

    #   """
    # ),

    # Add more prompts as needed
]

def scrape_website(url: str) -> Optional[str]:
    """Scrape website content with proper headers and rate limiting."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CommercialConstructionBot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    }
    
    try:
        # Add rate limiting
        time.sleep(1)  # Be nice to servers
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav']):
            element.decompose()
            
        # Get text with better formatting
        text = ' '.join([p.get_text(strip=True) for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'article'])])
        return text if text.strip() else None
        
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

def analyze_content(content: str, prompt: str) -> str:
    """Analyze content using Ollama with the provided prompt."""
    try:
        response = client.generate(
            model=MODEL_NAME, 
            prompt=prompt.format(content=content),
            stream=False
        )
        
        # Handle the response - Ollama returns the response directly in the 'response' field
        if isinstance(response, dict):
            return response.get('response', f"Error: Unexpected response format - {response}")
        else:
            # If response is not a dict, it might be the direct response string
            return str(response)

    except Exception as e:
        logger.error(f"Analysis error in analyze_content: {str(e)}")
        return f"Analysis error: {str(e)}"

def is_site_live(url: str) -> bool:
    """Check if the site is reachable."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code < 400  # Site is live if status code is less than 400
    except requests.exceptions.RequestException:
        return False

def extract_url_from_html(html_content: str) -> Optional[str]:
    """Extracts and decodes the URL from a given HTML <a> tag."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        a_tag = soup.find('a', href=True)  # Find the first <a> tag with an href attribute
        
        if not a_tag:
            return None
            
        raw_url = a_tag['href']
        
        # Handle JavaScript encoded URLs
        if "javascript:openPopupFocus" in raw_url:
            # Look for both http and https encoded patterns
            url_pattern = r"(?:http|https)%3A%2F%2F[-\w.]+(?:\/[-\w.%]*)*"
            match = re.search(url_pattern, raw_url)
            
            if match:
                encoded_url = match.group(0)
                # Decode the URL
                decoded_url = html.unescape(encoded_url)
                decoded_url = decoded_url.replace('%3A', ':').replace('%2F', '/')
                return decoded_url
                
        # Handle direct URLs
        elif raw_url.startswith(('http://', 'https://')):
            # Extract just the main URL without query parameters
            base_url = re.match(r'https?://[^?\s,\'\"]+', raw_url)
            if base_url:
                return base_url.group(0).rstrip('/')
            return raw_url.split('?')[0].rstrip('/')
        
        # Handle URLs without protocol
        elif raw_url.startswith('www.'):
            return f'http://{raw_url.split("?")[0].rstrip("/")}'
            
        return raw_url.split('?')[0].rstrip('/')
        
    except Exception as e:
        print(f"Error extracting URL: {e}")
        return None

def process_row(row: List[str]) -> Optional[List[str]]:
    """Process a single row of data."""
    try:
        if len(row) > 1:
            account_name = row[0].strip()
            raw_html = row[1].strip()

            # Extract and validate URL
            extracted_url = extract_url_from_html(raw_html)
            if not extracted_url:
                return [account_name, "", "N/A", "Failed to extract a valid URL."] + [""] * len(PROMPTS)

            # Check if site is live
            if not is_site_live(extracted_url):
                return [account_name, extracted_url, "No", "Site is not live"] + [""] * len(PROMPTS)

            # Scrape website content
            website_content = scrape_website(extracted_url)
            if not website_content or "Error:" in str(website_content):
                return [account_name, extracted_url, "Yes", "Scraping failed"] + [""] * len(PROMPTS)

            # Analyze content with each prompt
            results = []
            for _, prompt in PROMPTS:
                result = analyze_content(website_content, prompt)
                results.append(result)

            return [account_name, extracted_url, "Yes", ""] + results

    except Exception as e:
        print(f"Error processing row: {str(e)}")
        return [account_name, "", "N/A", f"Error: {str(e)}"] + [""] * len(PROMPTS)

def main():
    input_file = "input.csv"  # Path to your input CSV file
    output_file = f"output/output-{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"  # Output file with timestamp

    logger.info("\nStarting AI analysis...")
    logger.info(f"Looking for input file: {os.path.abspath(input_file)}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    logger.info(f"Output will be written to: {os.path.abspath(output_file)}")

    try:
        # Validate input file
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found at: {os.path.abspath(input_file)}")

        # Read input data
        logger.info("Reading input file...")
        with open(input_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)
            rows = list(reader)
            logger.info(f"Found {len(rows)} rows to process")

        if not rows:
            logger.warning(f"No data found in {input_file}")
            return

        # Create output file with header
        updated_header = ['Account Name', 'Website', 'Is Site Live', 'Error'] + [title for title, _ in PROMPTS]
        with open(output_file, mode='w', newline='', encoding='utf-8') as output_csv:
            writer = csv.writer(output_csv)
            writer.writerow(updated_header)

        # Process rows in parallel
        num_processes = min(multiprocessing.cpu_count(), len(rows))
        logger.info(f"\nInitializing {num_processes} worker processes...")
        
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = []
            for result in tqdm(
                pool.imap_unordered(process_row, rows),
                total=len(rows),
                desc="Processing accounts"
            ):
                if result:
                    results.append(result)

        # Write all results at once
        logger.info("\nWriting results to file...")
        with open(output_file, mode='a', newline='', encoding='utf-8') as output_csv:
            writer = csv.writer(output_csv)
            writer.writerows(results)

        # Verify output
        if os.path.exists(output_file):
            file_size = os.path.getsize(output_file)
            logger.info(f"\nProcessing complete!")
            logger.info(f"Results processed: {len(results)}")
            logger.info(f"Output file size: {file_size} bytes")
            
            logger.info("\nFirst few lines of output:")
            with open(output_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 5:
                        print(line.strip())
                    else:
                        break
        else:
            logger.warning("Warning: Output file was not created")

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
