"""
Company Score Calculator

This script reads the stage 1 output and calculates two scores for each company:
1. Frequency Score: Based on the frequency of keywords found
2. Weighted Score: Based on special keyword values provided

Input:
- output/stage_1_output.csv: Stage 1 output with keywords
- inputs/keyword_weights.csv: Special keyword values (format: keyword,weight)

Output:
- output/company_scores.csv: Companies with their calculated scores
"""

import pandas as pd
import logging
import os
from typing import Dict, List, Tuple
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default weights for special keywords if file not provided
DEFAULT_KEYWORD_WEIGHTS = {
    # 'design-build': 10,
    # 'commercial construction': 8,
    # 'general contractor': 7,
    # 'construction management': 6,
    # 'tenant improvements': 5,
    # 'pre-construction': 5,
    # 'industrial construction': 4,
    # 'commercial development': 4,
    # 'site development': 3,
    # 'project management': 3
}

def load_keyword_weights(weights_file: str) -> Dict[str, float]:
    """Load keyword weights from file or use defaults if file not found."""
    try:
        if os.path.exists(weights_file):
            weights_df = pd.read_csv(weights_file)
            return dict(zip(weights_df['keyword'].str.lower(), weights_df['weight']))
        else:
            logger.warning(f"Weights file not found: {weights_file}. Using default weights.")
            return DEFAULT_KEYWORD_WEIGHTS
    except Exception as e:
        logger.error(f"Error loading weights: {e}")
        return DEFAULT_KEYWORD_WEIGHTS

def extract_keywords(text: str) -> List[str]:
    """Extract keywords from text, handling various formats."""
    if pd.isna(text) or text in ['None', 'N/A']:
        return []
    
    # Convert to lowercase and split by comma
    keywords = [k.strip().lower() for k in text.split(',')]
    return [k for k in keywords if k]  # Remove empty strings

def calculate_frequency_score(keywords: List[str]) -> float:
    """Calculate score based on keyword frequency."""
    if not keywords:
        return 0.0
    
    # Basic frequency score: number of keywords found
    return len(keywords) * 1.0

def calculate_weighted_score(keywords: List[str], weights: Dict[str, float]) -> Tuple[float, List[str]]:
    """Calculate score based on keyword weights and return matched special keywords."""
    if not keywords:
        return 0.0, []
    
    score = 0.0
    matched_keywords = []
    
    for keyword in keywords:
        for special_keyword, weight in weights.items():
            if special_keyword in keyword:  # Partial match
                score += weight
                matched_keywords.append(f"{special_keyword} ({weight})")
                break
    
    return score, matched_keywords

def main():
    try:
        logger.info("\nStarting company score calculation...")
        
        # Define input/output paths
        stage1_path = 'output/stage_1_output.csv'
        weights_path = 'inputs/keyword_weights.csv'
        output_path = 'output/company_scores.csv'
        detailed_output_path = 'output/company_scores_detailed.csv'
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Load keyword weights
        keyword_weights = load_keyword_weights(weights_path)
        logger.info(f"Loaded {len(keyword_weights)} keyword weights")
        
        # Read stage 1 output
        if not os.path.exists(stage1_path):
            raise FileNotFoundError(f"Stage 1 output not found: {stage1_path}")
            
        df = pd.read_csv(stage1_path)
        logger.info(f"Processing {len(df)} companies")
        
        # Calculate scores for each company
        results = []
        for _, row in df.iterrows():
            keywords = extract_keywords(row['Keywords Found'])
            
            freq_score = calculate_frequency_score(keywords)
            weighted_score, matched_special = calculate_weighted_score(keywords, keyword_weights)
            
            results.append({
                'Account Name': row['Account Name'],
                'Website': row['Website'],
                'Is Site Live': row['Is Site Live'],
                'Keywords Found': row['Keywords Found'],
                'Number of Keywords': len(keywords),
                'Frequency Score': round(freq_score, 2),
                'Weighted Score': round(weighted_score, 2),
                'Special Keywords Matched': '; '.join(matched_special) if matched_special else 'None',
                'Raw Keywords List': ', '.join(keywords) if keywords else 'None'
            })
        
        # Create results DataFrame and sort by weighted score
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values(['Weighted Score', 'Frequency Score'], ascending=[False, False])
        
        # Save detailed results
        results_df.to_csv(detailed_output_path, index=False)
        
        # Create and save summary results
        summary_df = results_df[[
            'Account Name', 'Website', 'Is Site Live',
            'Number of Keywords', 'Frequency Score', 'Weighted Score',
            'Special Keywords Matched'
        ]]
        summary_df.to_csv(output_path, index=False)
        
        logger.info(f"Detailed results saved to: {detailed_output_path}")
        logger.info(f"Summary results saved to: {output_path}")
        
        # Print summary statistics
        print("\nScore Summary:")
        print("-" * 50)
        print(f"Total companies processed: {len(results_df)}")
        print(f"Companies with keywords found: {len(results_df[results_df['Number of Keywords'] > 0])}")
        print(f"Average number of keywords per company: {results_df['Number of Keywords'].mean():.2f}")
        print(f"Average Frequency Score: {results_df['Frequency Score'].mean():.2f}")
        print(f"Average Weighted Score: {results_df['Weighted Score'].mean():.2f}")
        print(f"Maximum Weighted Score: {results_df['Weighted Score'].max():.2f}")
        
        # Print distribution of scores
        print("\nScore Distribution:")
        print("-" * 50)
        score_ranges = [(0, 10), (10, 20), (20, 30), (30, 40), (40, float('inf'))]
        for low, high in score_ranges:
            count = len(results_df[
                (results_df['Weighted Score'] >= low) & 
                (results_df['Weighted Score'] < high)
            ])
            print(f"Score {low}-{high if high != float('inf') else '+'}: {count} companies")
        
    except Exception as e:
        logger.error(f"Error calculating scores: {e}")
        raise

if __name__ == "__main__":
    main() 