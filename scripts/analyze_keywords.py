"""
Keyword Analysis Script

This script reads the output CSV files, extracts unique keywords from the last column,
and generates frequency reports.

Output:
- output/keyword_frequency.txt: Text report showing unique keywords and their frequencies
- output/keyword_frequency.csv: CSV file with keyword frequencies for further analysis
"""

import pandas as pd
import os
import glob
from collections import Counter
import logging
import re
import csv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Common short words to filter out
COMMON_WORDS = {
    'the', 'and', 'for', 'that', 'this', 'with', 'are', 'was', 'were', 'will',
    'have', 'has', 'had', 'not', 'but', 'they', 'from', 'you', 'can', 'all',
    'get', 'just', 'more', 'now', 'out', 'see', 'use', 'who', 'way', 'new',
    'any', 'day', 'who', 'its', 'it', 'is', 'to', 'in', 'of', 'on', 'at', 'by',
    'an', 'be', 'as', 'or', 'do', 'if', 'my', 'up', 'so', 'me', 'he', 'we',
    'no', 'yes', 'our', 'one', 'his', 'her', 'their', 'there', 'here', 'when',
    'what', 'why', 'how', 'which', 'where', 'who', 'whom', 'these', 'those'
}

def extract_response_keywords(text: str) -> list:
    """Extract keywords from text and clean them."""
    if pd.isna(text):
        return []
    
    # Convert to lowercase and remove special characters
    text = text.lower()
    text = re.sub(r'[^\w\s,]', ' ', text)
    
    # Split by both commas and spaces
    words = []
    # First split by comma
    comma_splits = text.split(',')
    for split in comma_splits:
        # Then split by space
        space_splits = split.strip().split()
        words.extend(space_splits)
    
    # Clean and filter words
    cleaned_words = []
    for word in words:
        word = word.strip()
        # Skip if word:
        # - is empty
        # - is in common words list
        # - is shorter than 5 characters
        # - contains numbers
        # - is just numbers
        if (word and 
            len(word) > 4 and 
            word not in COMMON_WORDS and 
            not any(char.isdigit() for char in word) and
            not word.isnumeric()):
            cleaned_words.append(word)
    
    return cleaned_words

def analyze_output_files():
    """Analyze all output CSV files and generate keyword frequency reports."""
    try:
        # Find all output files
        output_files = glob.glob('output/output-*.csv')
        if not output_files:
            logger.error("No output files found")
            return
        
        latest_file = max(output_files)  # Get the most recent file
        logger.info(f"Analyzing file: {latest_file}")
        
        # Initialize counter for all keywords
        keyword_counter = Counter()
        
        # Process the file
        df = pd.read_csv(latest_file)
        # Get the last column (keywords column)
        keywords_col = df.iloc[:, -1]
        
        # Process each row's keywords
        for keywords_str in keywords_col:
            keywords = extract_response_keywords(str(keywords_str))
            keyword_counter.update(keywords)
        
        # Sort by frequency (descending)
        sorted_keywords = sorted(keyword_counter.items(), key=lambda x: x[1], reverse=True)
        
        # Generate text report
        report = "Keyword Frequency Report\n"
        report += "=====================\n\n"
        report += f"Total unique keywords found: {len(sorted_keywords)}\n"
        report += "Note: Common words and words shorter than 5 characters have been filtered out\n\n"
        report += "Frequency | Keyword\n"
        report += "-" * 50 + "\n"
        
        for keyword, count in sorted_keywords:
            report += f"{count:9d} | {keyword}\n"
        
        # Save text report
        txt_output_path = 'output/keyword_frequency.txt'
        with open(txt_output_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        # Save CSV report
        csv_output_path = 'output/keyword_frequency.csv'
        with open(csv_output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Keyword', 'Frequency'])  # Write header
            writer.writerows(sorted_keywords)  # Write data
            
        logger.info(f"Text report generated: {txt_output_path}")
        logger.info(f"CSV report generated: {csv_output_path}")
        
        # Print summary to console
        if sorted_keywords:
            print("\nAll keywords by frequency (most frequent first):")
            print("-" * 50)
            print("Count | Keyword")
            print("-" * 50)
            for keyword, count in sorted_keywords:
                print(f"{count:5d} | {keyword}")
            print("-" * 50)
            print(f"Total unique keywords: {len(sorted_keywords)}")
            print(f"\nReports saved to:")
            print(f"- Text report: {txt_output_path}")
            print(f"- CSV report: {csv_output_path}")
        else:
            print("\nNo keywords found")
            
    except Exception as e:
        logger.error(f"Error analyzing keywords: {str(e)}")
        raise

if __name__ == "__main__":
    analyze_output_files() 