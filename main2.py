from bs4 import BeautifulSoup
import requests
import time
from typing import Optional
import csv  # Import the csv module
import re  # For pattern matching
import html  # For decoding HTML entities


def scrape_website(url: str) -> Optional[str]:
    """Scrape website content with proper headers and rate limiting."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; CommercialConstructionBot/1.0)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9',
    }

    try:
        time.sleep(1)  # Be nice to servers
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove unwanted elements
        for element in soup(['script', 'style', 'header', 'footer', 'nav']):
            element.decompose()

        # Get text with better formatting
        text = ' '.join([p.get_text(strip=True) for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'article'])])

        # Print the cleaned content for debugging (first 1000 characters)
        print("Cleaned Website Content (First 1000 characters):")
        print(text[:1000])

        return text if text.strip() else None

    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"

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

def analyze_content(content: str) -> tuple:
    """Analyze content for keywords and count their occurrences."""
    keywords = [
        "pre-construction", "construction management", "design build", "design-build",
        "tenant improvements", "commercial", "commercial gc", "commercial general contractor", "general contracting"
    ]

    content_lower = content.lower()

    keyword_counts = {keyword: len(re.findall(r'\b' + re.escape(keyword) + r'\b', content_lower)) for keyword in keywords}

    print("Keyword Counts:")
    for keyword, count in keyword_counts.items():
        print(f"{keyword}: {count}")

    found_keywords = [keyword for keyword, count in keyword_counts.items() if count > 0]

    return found_keywords, sum(keyword_counts[keyword] for keyword in found_keywords)

def main():
    csv_file = "/Users/connorfulk/Git_Repo/hound-ai/urlsSHORT.csv - Sheet1.csv"  # Replace with the path to your CSV file
    output_file = "/Users/connorfulk/Git_Repo/hound-ai/urls_with_keywords_final.csv"  # New CSV output file

    try:
        with open(csv_file, newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            header = next(reader)  # Read the header row

            # Define the updated header for the output file
            updated_header = ['Account Name', 'Website', 'Keywords Found', 'Keyword Count']

            with open(output_file, mode='w', newline='', encoding='utf-8') as output_csv:
                writer = csv.writer(output_csv)
                writer.writerow(updated_header)

                for row_index, row in enumerate(reader, start=2):  # Start from Row 2
                    if len(row) > 1:  # Ensure the row has at least two columns
                        account_name = row[0].strip()  # Assume the account name is in Column A
                        raw_html = row[1].strip()  # Assume the HTML content is in Column B
                        print(f"\nExtracting URL from HTML at Row {row_index}: {raw_html}")

                        extracted_url = extract_url_from_html(raw_html)
                        if not extracted_url:
                            print("Failed to extract a valid URL.")
                            continue

                        print(f"Extracted URL: {extracted_url}")
                        website_content = scrape_website(extracted_url)
                        if not website_content or "Error:" in str(website_content):
                            print(f"Scraping failed: {website_content}")
                            continue

                        keywords, keyword_count = analyze_content(website_content)

                        # Write the result to the output CSV
                        writer.writerow([account_name, extracted_url, ', '.join(keywords), keyword_count])

                        print("\nAnalysis Results:")
                        print("-" * 50)
                        print(f"Account Name: {account_name}")
                        print(f"Keywords Found: {', '.join(keywords)}")
                        print(f"Keyword Count: {keyword_count}")

    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
