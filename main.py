from bs4 import BeautifulSoup
import requests
import ollama
import time
from typing import Optional
import re  # For pattern matching
import html  # For decoding HTML entities
import csv  # Import the csv module
import os
from datetime import datetime

# Initialize the model
try:
    client = ollama.Client()
    # Using the latest llama2 model
    MODEL_NAME = "llama2"
except Exception as e:
    print(f"Error initializing Ollama: {e}")
    exit(1)

PROMPTS = [

    (
        "Count Keywords", 
        """
          count the number of times the keywords appear in the content. 
          Keywords:
        [
            "pre-construction", "construction management", "design build", "design-build",
            "tenant improvements", "commercial", "commercial gc", "commercial general contractor", "general contracting"
        ]    
        """
    ),
    # (
    #     "Main Services and Markets", 
    #     """
    #         Tell me the main services and markets that this company performs and tell me what pages you received the specific service-related keywords related within the website corresponding to each keyword. 
    #         Content:
    #         {content[:4000]}  # Limit content length to avoid token limits
    #     """
    # ),
    # (
    #     "Keyword Analysis", 
    #     """
    #         Analyze the content for keywords related to commercial general contracting like pre-construction, construction management, design build or design-build, tenant improvements.
    #         Ignore the words from companies blogs or article pages. 
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
        response = client.generate(model=MODEL_NAME, 
                                   prompt=prompt.format(content=content),
                                   stream=False)  # Set to True if you want to stream responses
        return response['response']
      
        # # Print the response for debugging
        # print(f"Response from Ollama: {response}")

        # # Check if the response is a dictionary and contains the 'response' key
        # if isinstance(response, dict) and 'response' in response:
        #     return response['response']
        # else:
        #     return f"Unexpected response format: {response}"  # Handle unexpected response format
    except Exception as e:
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
    soup = BeautifulSoup(html_content, 'html.parser')
    a_tag = soup.find('a', href=True)  # Find the first <a> tag with an href attribute
    if a_tag:
        raw_url = a_tag['href']
        # Check if the URL is JavaScript encoded
        if "javascript:openPopupFocus" in raw_url:
            match = re.search(r"http%3A%2F%2F[-\w.]+", raw_url)
            if match:
                encoded_url = match.group()
                decoded_url = html.unescape(encoded_url)
                decoded_url = decoded_url.replace('%3A', ':').replace('%2F', '/')
                return decoded_url
        return a_tag['href']  # Return the raw href if not encoded
    return None


def main():
    input_file = "input.csv"  # Path to your input CSV file
    output_file = f"output/output-{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"  # Output file with timestamp

    try:
        with open(input_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Define the updated header for the output file
            updated_header = ['Account Name', 'Website', 'Is Site Live', 'Error'] + [title for title, _ in PROMPTS]

            with open(output_file, mode='w', newline='', encoding='utf-8') as output_csv:
                writer = csv.writer(output_csv)
                writer.writerow(updated_header)

                for row_index, row in enumerate(reader, start=2):  # Start from Row 2
                    try:
                        if len(row) > 1:  # Ensure the row has at least two columns
                            account_name = row[0].strip()  # Assume the account name is in Column A
                            raw_html = row[1].strip()  # Assume the HTML content is in Column B
                            print(f"\nExtracting URL from HTML at Row {row_index}: {raw_html}")

                            extracted_url = extract_url_from_html(raw_html)
                            if not extracted_url:
                                error_message = "Failed to extract a valid URL."
                                print(error_message)
                                writer.writerow([account_name, "", "N/A", error_message])  # Write error to output CSV
                                continue

                            print(f"Extracted URL: {extracted_url}")
                            if not is_site_live(extracted_url):
                                print(f"Site is not live: {extracted_url}")
                                writer.writerow([account_name, extracted_url, "No", "Site is not live"])  # Log site status
                                continue

                            website_content = scrape_website(extracted_url)
                            if not website_content or "Error:" in str(website_content):
                                print(f"Scraping failed: {website_content}")
                                writer.writerow([account_name, extracted_url, "Yes", "Scraping failed"])  # Log scraping status
                                continue

                            # Iterate through the prompts and analyze the content
                            results = []
                            for title, prompt in PROMPTS:
                                result = analyze_content(website_content, prompt)
                                results.append(result)

                            # Write the results to the output CSV
                            writer.writerow([account_name, extracted_url, "Yes", ""] + results)

                            print("\nAnalysis Results:")
                            print("-" * 50)
                            print(f"Account Name: {account_name}")
                            print(f"Is Site Live: Yes")
                            for title, result in zip([t for t, _ in PROMPTS], results):
                                print(f"{title}: {result}")

                    except Exception as e:
                        print(f"An error occurred while processing row {row_index}: {e}")
                        writer.writerow([account_name, "", "N/A", f"Error: {str(e)}"])  # Log the error

    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
