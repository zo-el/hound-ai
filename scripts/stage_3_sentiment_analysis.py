"""
Stage 3 Sentiment Analysis Processor

This script analyzes qualitative data from both Salesforce and outreach records to provide
a comprehensive view of account sentiment, engagement, and sales progression.

Input Files:
- output/stage_2_output.csv: Enhanced account data from stage 2
- inputs/salesforce.csv: Salesforce data with detailed account history
- inputs/outreach.csv: Outreach activity and engagement data

Output:
- output/stage_3_output.csv: Account data with sentiment analysis
- output/stage_3_summary.md: Summary report
"""

import pandas as pd
import numpy as np
from datetime import datetime
import multiprocessing
import logging
import os
from typing import Dict, List, Optional
import re
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Analysis configuration
SENTIMENT_PATTERNS = {
    'positive': [
        r'(?i)interested',
        r'(?i)good call',
        r'(?i)follow[ -]?up',
        r'(?i)great',
        r'(?i)demo scheduled',
        r'(?i)send.+information',
        r'(?i)looking.+switch',
        r'(?i)evaluating',
        r'(?i)demo.+confirmed'
    ],
    'negative': [
        r'(?i)not interested',
        r'(?i)no budget',
        r'(?i)too expensive',
        r'(?i)ghosted',
        r'(?i)unresponsive',
        r'(?i)hung up',
        r'(?i)no need',
        r'(?i)happy.+current',
        r'(?i)too small'
    ],
    'objections': [
        r'(?i)price|cost|expensive',
        r'(?i)timing|not ready',
        r'(?i)too small',
        r'(?i)happy with current',
        r'(?i)no need',
        r'(?i)budget',
        r'(?i)using competitor'
    ]
}

def calculate_temporal_weight(date_str: str) -> float:
    """Calculate weight based on how recent the interaction is."""
    try:
        if pd.isna(date_str):
            return 0.1
            
        date = pd.to_datetime(date_str, errors='coerce')
        if pd.isna(date):
            return 0.1
            
        days_ago = (pd.Timestamp.now() - date).days
        
        if days_ago <= 365:  # Within 1 year
            return 1.0
        elif days_ago <= 730:  # Within 2 years
            return 0.7
        elif days_ago <= 1095:  # Within 3 years
            return 0.4
        else:
            return 0.2
    except Exception as e:
        logger.warning(f"Error calculating temporal weight for date {date_str}: {str(e)}")
        return 0.1

def analyze_text(text: str) -> Dict:
    """Analyze text for sentiment patterns."""
    if pd.isna(text):
        return {'positive': 0, 'negative': 0, 'objections': [], 'matched_patterns': {'positive': [], 'negative': []}}
    
    results = {
        'positive': 0,
        'negative': 0,
        'objections': [],
        'matched_patterns': {
            'positive': [],
            'negative': []
        }
    }
    
    for pos_pattern in SENTIMENT_PATTERNS['positive']:
        if re.search(pos_pattern, text):
            results['positive'] += 1
            match = re.search(pos_pattern, text).group()
            results['matched_patterns']['positive'].append(f"{match} (pattern: {pos_pattern})")
            
    for neg_pattern in SENTIMENT_PATTERNS['negative']:
        if re.search(neg_pattern, text):
            results['negative'] += 1
            match = re.search(neg_pattern, text).group()
            results['matched_patterns']['negative'].append(f"{match} (pattern: {neg_pattern})")
            
    for obj_pattern in SENTIMENT_PATTERNS['objections']:
        if re.search(obj_pattern, text):
            results['objections'].append(obj_pattern.replace('(?i)', '').split('|')[0])
            
    return results

def process_account(account_data: tuple) -> Optional[Dict]:
    """Process all data for a single account."""
    try:
        account_name, records = account_data
        
        # Initialize metrics
        total_sentiment = 0
        engagement_score = 0
        all_objections = []
        data_points = len(records)
        matched_patterns = {'positive': [], 'negative': []}
        
        # Calculate data confidence
        latest_activity = pd.to_datetime(records['Date'].max())
        days_since_latest = (pd.Timestamp.now() - latest_activity).days
        
        if data_points >= 5 and days_since_latest <= 365:
            data_confidence = 'High'
        elif data_points >= 2 and days_since_latest <= 730:
            data_confidence = 'Medium'
        else:
            data_confidence = 'Low'
        
        # Get latest status
        latest_status = records.sort_values('Date', ascending=False).iloc[0].get('Call Result', 'Unknown')
        
        # Process each record
        for _, record in records.iterrows():
            weight = calculate_temporal_weight(record['Date'])
            
            # Analyze text fields
            text_fields = [
                record.get('BDR Next Step', ''),
                record.get('Lead Score Reason Description', ''),
                record.get('Reason for Win/Loss - Description', ''),
                record.get('Qualification Notes', ''),
                record.get('Comments', '')
            ]
            
            combined_text = ' '.join(str(field) for field in text_fields if pd.notna(field))
            sentiment_results = analyze_text(combined_text)
            
            # Update metrics
            sentiment_score = (sentiment_results['positive'] - sentiment_results['negative']) * weight
            total_sentiment += sentiment_score
            
            matched_patterns['positive'].extend(sentiment_results['matched_patterns']['positive'])
            matched_patterns['negative'].extend(sentiment_results['matched_patterns']['negative'])
            
            # Add engagement signals
            try:
                call_duration = float(str(record.get('Call Duration', 0)).strip() or 0)
                if call_duration > 0:
                    engagement_score += min(call_duration / 60.0, 1.0) * weight
            except (ValueError, TypeError):
                logger.warning(f"Invalid call duration for {account_name}")
            
            all_objections.extend(sentiment_results['objections'])
        
        # Normalize scores
        normalized_sentiment = total_sentiment / max(data_points, 1)
        normalized_engagement = (engagement_score / max(data_points, 1)) * 100
        
        # Determine interest level
        if normalized_sentiment > 0.5 and normalized_engagement > 50:
            interest_level = 'High'
        elif normalized_sentiment > 0 and normalized_engagement > 25:
            interest_level = 'Medium'
        elif normalized_sentiment > -0.5:
            interest_level = 'Low'
        else:
            interest_level = 'None'
        
        return {
            'Account Name': account_name,
            'Latest Status': latest_status,
            'Engagement Score': round(normalized_engagement, 2) if normalized_engagement > 0 else 'No Engagement',
            'Sentiment Score': round(normalized_sentiment, 2),
            'Interest Level': interest_level,
            'Key Objections': ', '.join(set(all_objections)) if all_objections else 'None identified',
            'Latest Activity': records['Date'].max(),
            'Data Confidence': data_confidence,
            'Positive Patterns': '; '.join(set(matched_patterns['positive'])) if matched_patterns['positive'] else 'None',
            'Negative Patterns': '; '.join(set(matched_patterns['negative'])) if matched_patterns['negative'] else 'None'
        }
        
    except Exception as e:
        logger.error(f"Error processing account {account_name}: {str(e)}")
        return None

def generate_summary_report(df: pd.DataFrame, output_path: str):
    """Generate summary report of the analysis."""
    try:
        total_accounts = len(df)
        
        engagement_scores = pd.to_numeric(
            df['Engagement Score'].mask(df['Engagement Score'] == 'No Engagement', 0),
            errors='coerce'
        )
        
        report = f"""# Sentiment Analysis Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
Total Accounts: {total_accounts}
Average Engagement: {engagement_scores.mean():.2f}
Average Sentiment: {df['Sentiment Score'].mean():.2f}

## Interest Levels
{df['Interest Level'].value_counts().to_string()}

## Data Confidence
{df['Data Confidence'].value_counts().to_string()}

## Key Statistics
- High Interest Accounts: {len(df[df['Interest Level'] == 'High'])}
- Recent Activity (< 90 days): {len(df[pd.to_datetime(df['Latest Activity']) > pd.Timestamp.now() - pd.Timedelta(days=90)])}
- No Engagement: {len(df[df['Engagement Score'] == 'No Engagement'])}
"""

        with open(output_path, 'w') as f:
            f.write(report)
            
    except Exception as e:
        logger.error(f"Error generating summary report: {str(e)}")

def main():
    """Main execution function."""
    try:
        logger.info("\nStarting stage 3 processing...")
        
        # Define paths
        stage2_path = 'output/stage_2_output.csv'
        outreach_path = 'inputs/outreach.csv'
        salesforce_path = 'inputs/salesforce.csv'
        output_path = 'output/stage_3_output.csv'
        summary_path = 'output/stage_3_summary.md'
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Validate input files
        for path in [stage2_path, outreach_path, salesforce_path]:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Input file not found: {path}")
        
        # Read input files
        logger.info("Reading input files...")
        stage2_df = pd.read_csv(stage2_path)
        outreach_df = pd.read_csv(outreach_path)
        salesforce_df = pd.read_csv(salesforce_path)
        
        # Merge datasets
        logger.info("Merging datasets...")
        combined_df = pd.merge(
            stage2_df,
            salesforce_df,
            on='Account Name',
            how='left'
        )
        
        combined_df = pd.merge(
            combined_df,
            outreach_df,
            left_on='Account Name',
            right_on='Account: Account Name',
            how='left'
        )
        
        # Process accounts in parallel
        account_groups = list(combined_df.groupby('Account Name'))
        num_processes = min(multiprocessing.cpu_count(), len(account_groups))
        
        logger.info(f"Processing {len(account_groups)} accounts using {num_processes} processes...")
        
        with multiprocessing.Pool(processes=num_processes) as pool:
            results = []
            for result in tqdm(
                pool.imap_unordered(process_account, account_groups),
                total=len(account_groups),
                desc="Processing accounts"
            ):
                if result is not None:
                    results.append(result)
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Save results
        logger.info(f"Saving results to {output_path}")
        results_df.to_csv(output_path, index=False)
        
        # Generate and save summary
        logger.info("Generating summary report...")
        generate_summary_report(results_df, summary_path)
        
        # Verify output
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"\nOutput file size: {file_size} bytes")
            
            logger.info("\nFirst few lines of output:")
            with open(output_path, 'r') as f:
                for i, line in enumerate(f):
                    if i < 5:
                        print(line.strip())
                    else:
                        break
        else:
            logger.warning("Warning: Output file was not created")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 