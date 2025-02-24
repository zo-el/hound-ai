from bs4 import BeautifulSoup
import requests
import csv
import re
import html
import os
from typing import Optional, List, Tuple
import multiprocessing
from functools import partial
from tqdm import tqdm

# Define the keywords to search for
KEYWORDS = [
    "commercial construction", "general contractor", "construction management", "construction services", 
    "project management", "contracting", "construction firm", "building contractor", "developer", 
    "general construction", "contractor services", "professional services", "project developer", 
    "commercial development", "commercial building", "retail construction", "industrial construction", 
    "office space construction", "tenant improvements", "structural engineering", 
    "interior buildouts", "design-build", "pre-construction services", "site development", "ground-up construction", 
    "General Contractors", "Commercial", "Healthcare", "industrial"
]

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

def is_site_live(url: str) -> bool:
    """Check if the site is reachable."""
    try:
        response = requests.head(url, timeout=10)
        return response.status_code < 400  # Site is live if status code is less than 400
    except requests.exceptions.RequestException:
        return False

def scrape_website(url: str) -> Optional[str]:
    """Scrape website content with proper headers."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; KeywordScraperBot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    }
    
    try:
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
        print(f"Error scraping {url}: {str(e)}")
        return None

def find_keywords(content: str) -> List[Tuple[str, str]]:
    """Find keywords in the content and return their locations."""
    found_keywords = []
    for keyword in KEYWORDS:
        keyword_lower = keyword.lower()
        if keyword_lower in content.lower():
            # Find the index of the keyword in the content
            start_index = content.lower().index(keyword_lower)
            end_index = start_index + len(keyword)
            
            # Get a snippet of text around the keyword for context
            snippet_start = max(0, start_index - 30)  # Get 30 characters before the keyword
            snippet_end = min(len(content), end_index + 30)  # Get 30 characters after the keyword
            context = content[snippet_start:snippet_end].replace('\n', ' ').strip()  # Clean up newlines
            
            # Add the keyword and its context to the found list
            found_keywords.append((keyword, f"Found in content: '{context}'"))
    return found_keywords

def process_row(row: List[str]) -> Optional[List[str]]:
    """Process a single row of data."""
    try:
        if len(row) > 1:
            account_name = row[0].strip()
            raw_html = row[1].strip()

            extracted_url = extract_url_from_html(raw_html)
            if not extracted_url:
                return [account_name, "", "N/A", "Failed to extract a valid URL.", ""]

            if not is_site_live(extracted_url):
                return [account_name, extracted_url, "No", "N/A", "Site is not live"]

            website_content = scrape_website(extracted_url)
            if not website_content:
                return [account_name, extracted_url, "Yes", "N/A", "Scraping failed"]

            keywords_found = find_keywords(website_content)
            if keywords_found:
                keywords_str = ', '.join([kw[0] for kw in keywords_found])
                proof_str = ', '.join([kw[1] for kw in keywords_found])
            else:
                keywords_str = "None"
                proof_str = "N/A"

            return [account_name, extracted_url, "Yes", keywords_str, proof_str]

    except Exception as e:
        return [account_name, "", "N/A", "Error", f"Error: {str(e)}"]

def main():
    # Update input and output paths
    input_file = "inputs/input.csv"  # Update to correct input path
    output_file = "output/stage_1_output.csv"
    
    print(f"\nStarting script...")
    print(f"Looking for input file: {os.path.abspath(input_file)}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    print(f"Output will be written to: {os.path.abspath(output_file)}")

    try:
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found at: {os.path.abspath(input_file)}")

        # Read all rows from input file
        print("Reading input file...")
        with open(input_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Skip header
            print(f"Header found: {header}")
            rows = list(reader)
            print(f"Found {len(rows)} rows to process")

        if not rows:
            print(f"Warning: No data found in {input_file}")
            return

        # Create output file with header
        print("Creating output file...")
        with open(output_file, mode='w', newline='', encoding='utf-8') as output_csv:
            writer = csv.writer(output_csv)
            writer.writerow(['Account Name', 'Website', 'Is Site Live', 'Keywords Found', 'Proof'])

        # Create a pool of workers
        num_processes = min(multiprocessing.cpu_count(), len(rows))  # Don't create more processes than rows
        print(f"\nInitializing {num_processes} worker processes...")
        pool = multiprocessing.Pool(processes=num_processes)

        # Process rows in parallel with progress bar
        print(f"Processing {len(rows)} URLs using {num_processes} processes...")
        results = []
        for row_data in tqdm(pool.imap_unordered(process_row, rows), total=len(rows)):
            if row_data:
                results.append(row_data)

        pool.close()
        pool.join()

        # Write all results at once
        print("\nWriting results to file...")
        with open(output_file, mode='a', newline='', encoding='utf-8') as output_csv:
            writer = csv.writer(output_csv)
            writer.writerows(results)

        # Verify output was written
        if os.path.exists(output_file):
            print(f"\nProcessing complete!")
            print(f"Results processed: {len(results)}")
            print(f"Output written to: {os.path.abspath(output_file)}")
            
            # Check output file size
            file_size = os.path.getsize(output_file)
            print(f"Output file size: {file_size} bytes")
            
            # Read and print first few lines of output
            print("\nFirst few lines of output:")
            with open(output_file, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f):
                    if i < 5:  # Print first 5 lines
                        print(line.strip())
                    else:
                        break
        else:
            print("\nWarning: Output file was not created")

    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    # Protect against recursive multiprocessing on Windows
    multiprocessing.freeze_support()
    main() 