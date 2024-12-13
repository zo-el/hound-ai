from bs4 import BeautifulSoup
import requests
import ollama
import time
from typing import Optional

# Initialize the model
try:
    client = ollama.Client()
    # Using the latest llama2 model
    MODEL_NAME = "llama2"
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
    try:
        prompt = f"""Please analyze the following website content related to commercial construction:
1. Extract key phrases related to commercial construction
2. Identify main construction services or specialties
3. Note any specific industry terminology
4. Identify the company's main services or specialties
5. Identify if the company is going to require a crm system

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
    url = "https://dynamiccrest.in"  # Replace with the URL you want to analyze
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
