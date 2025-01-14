from bs4 import BeautifulSoup
import requests
import ollama
import time
from typing import Optional

# Initialize the model
try:
    client = ollama.Client()
    # Using the latest llama2 model
    MODEL_NAME = "llama-3-8b-web"
except Exception as e:
    print(f"Error initializing Ollama: {e}")
    exit(1)

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

def analyze_content(content: str) -> str:
    """Analyze content using Ollama with improved prompt."""
    try: # Re-write prompt to tell ai what keywords to search for within the website
        prompt = f"""Tell me the main services and markets that this company performs and tell me what pages you received the specific service-related keywords related within the website corresponding to each keyword. Ignore the words from companies blogs or article pages. I would suggest highlighting keywords related to commercial general contracting like pre-construction, construction management, design build or design-build, tenant improvements. 
Content:
{content[:4000]}  # Limit content length to avoid token limits
"""
        response = client.generate(model=MODEL_NAME, 
                                 prompt=prompt,
                                 stream=False)  # Set to True if you want to stream responses
        return response['response']
    except Exception as e:
        return f"Analysis error: {str(e)}"

def main():
    url = "http://consecogroup.com"  # Replace with the URL you want to analyze
    print(f"Analyzing: {url}")
    
    website_content = scrape_website(url)
    if not website_content or "Error:" in str(website_content):
        print(f"Scraping failed: {website_content}")
        return
        
    result = analyze_content(website_content)
    print("\nAnalysis Results:")
    print("-" * 50)
    print(result)

if __name__ == "__main__":
    main()
