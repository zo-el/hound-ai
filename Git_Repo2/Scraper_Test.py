from bs4 import BeautifulSoup
import requests
from rake_nltk import Rake

url = "http://rushresources.com/"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# Extract visible text
text = " ".join([p.get_text() for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])])

# Use RAKE for keyword extraction
rake = Rake()
rake.extract_keywords_from_text(text)
keywords = rake.get_ranked_phrases()

print(keywords)