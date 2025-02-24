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
from datetime import datetime, timedelta
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import re

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
    """
    Calculate weight based on how recent the interaction is.
    Returns weight between 0 and 1.
    """
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

def analyze_text(text: str, patterns: Dict[str, List[str]]) -> Dict:
    """Analyze text for sentiment patterns with pattern matching."""
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
    
    for pos_pattern in patterns['positive']:
        if re.search(pos_pattern, text):
            results['positive'] += 1
            match = re.search(pos_pattern, text).group()
            results['matched_patterns']['positive'].append(f"{match} (pattern: {pos_pattern})")
            
    for neg_pattern in patterns['negative']:
        if re.search(neg_pattern, text):
            results['negative'] += 1
            match = re.search(neg_pattern, text).group()
            results['matched_patterns']['negative'].append(f"{match} (pattern: {neg_pattern})")
            
    for obj_pattern in patterns['objections']:
        if re.search(obj_pattern, text):
            results['objections'].append(obj_pattern.replace('(?i)', '').split('|')[0])
            
    return results

def process_account(account_data: Tuple[str, pd.DataFrame]) -> Dict:
    """Process all data for a single account."""
    account_name, records = account_data
    logger.debug(f"Processing account: {account_name} with {len(records)} records")
    
    # Initialize metrics
    total_sentiment = 0
    engagement_score = 0
    all_objections = []
    data_points = len(records)
    matched_patterns = {'positive': [], 'negative': []}
    
    # Calculate data confidence based on:
    # - Number of data points
    # - Recency of data
    # - Quality of interactions
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
    
    # Calculate weighted sentiment and engagement
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
        sentiment_results = analyze_text(combined_text, SENTIMENT_PATTERNS)
        
        # Update metrics
        sentiment_score = (sentiment_results['positive'] - sentiment_results['negative']) * weight
        total_sentiment += sentiment_score
        
        # Track matched patterns
        matched_patterns['positive'].extend(sentiment_results['matched_patterns']['positive'])
        matched_patterns['negative'].extend(sentiment_results['matched_patterns']['negative'])
        
        # Add engagement signals - handle string conversion
        try:
            call_duration = record.get('Call Duration', 0)
            if pd.notna(call_duration):
                # Convert to float, handling empty strings and non-numeric values
                call_duration = float(str(call_duration).strip() or 0)
                if call_duration > 0:
                    engagement_score += min(call_duration / 60.0, 1.0) * weight  # Normalize to max 1 per call
        except (ValueError, TypeError):
            # Log warning for invalid call duration
            logger.warning(f"Invalid call duration value for {account_name}: {record.get('Call Duration')}")
            call_duration = 0
        
        # Add objections
        all_objections.extend(sentiment_results['objections'])
    
    # Normalize scores
    normalized_sentiment = total_sentiment / max(data_points, 1)  # -1 to 1 scale
    normalized_engagement = (engagement_score / max(data_points, 1)) * 100  # 0 to 100 scale
    normalized_data_points = min(data_points / 10, 1.0)  # 0 to 1 scale, caps at 10 data points
    
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
        'Data Points': normalized_data_points,
        'Data Confidence': data_confidence,
        'Positive Patterns Found': '; '.join(set(matched_patterns['positive'])) if matched_patterns['positive'] else 'None',
        'Negative Patterns Found': '; '.join(set(matched_patterns['negative'])) if matched_patterns['negative'] else 'None'
    }

def generate_summary_report(df: pd.DataFrame):
    """Generate summary report of the analysis."""
    # Calculate metrics
    total_accounts = len(df)
    
    # Handle engagement scores more safely
    engagement_scores = df['Engagement Score'].copy()
    engagement_scores = pd.to_numeric(engagement_scores.mask(engagement_scores == 'No Engagement', 0), 
                                    errors='coerce')
    avg_engagement = engagement_scores.mean()
    
    # Handle sentiment scores
    avg_sentiment = df['Sentiment Score'].mean()
    
    interest_dist = df['Interest Level'].value_counts()
    
    # Get objection counts
    objections = pd.Series([obj for objs in df['Key Objections'].str.split(', ') 
                          for obj in objs if obj != 'None identified'])
    top_objections = objections.value_counts().head()
    
    # Calculate days since latest activity
    now = pd.Timestamp.now()
    df['Days Since Activity'] = (now - pd.to_datetime(df['Latest Activity'])).dt.days
    
    # Calculate engagement distribution
    engagement_dist = {
        'High (>75)': len(engagement_scores[engagement_scores > 75]),
        'Medium (25-75)': len(engagement_scores[(engagement_scores >= 25) & (engagement_scores <= 75)]),
        'Low (<25)': len(engagement_scores[engagement_scores < 25]),
        'No Engagement': len(df[df['Engagement Score'] == 'No Engagement'])
    }
    
    # Format the report
    report = f"""# Sentiment Analysis Summary Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview
Total Accounts Analyzed: {total_accounts}
Average Engagement Score (excluding no engagement): {avg_engagement:.2f}
Average Sentiment Score: {avg_sentiment:.2f}

## Engagement Distribution
High (>75): {engagement_dist['High (>75)']}
Medium (25-75): {engagement_dist['Medium (25-75)']}
Low (<25): {engagement_dist['Low (<25)']}
No Engagement: {engagement_dist['No Engagement']}

## Interest Level Distribution
High: {interest_dist.get('High', 0)}
Medium: {interest_dist.get('Medium', 0)}
Low: {interest_dist.get('Low', 0)}
None: {interest_dist.get('None', 0)}

## Most Common Objections
{chr(10).join(f"- {obj}: {count}" for obj, count in top_objections.items())}

## Data Quality
High Confidence Records: {len(df[df['Data Confidence'] == 'High'])}
Medium Confidence Records: {len(df[df['Data Confidence'] == 'Medium'])}
Low Confidence Records: {len(df[df['Data Confidence'] == 'Low'])}

## Activity Timeline
Accounts with activity in last year: {len(df[df['Days Since Activity'] <= 365])}
Accounts with activity 1-2 years ago: {len(df[(df['Days Since Activity'] > 365) & (df['Days Since Activity'] <= 730)])}
Accounts with activity 2-3 years ago: {len(df[(df['Days Since Activity'] > 730) & (df['Days Since Activity'] <= 1095)])}
Accounts with no activity for 3+ years: {len(df[df['Days Since Activity'] > 1095])}
"""

    with open('output/stage_3_summary.md', 'w') as f:
        f.write(report)

def main():
    """Main execution function."""
    try:
        logger.info("Starting stage 3 processing...")
        
        # Read input files
        stage2_df = pd.read_csv('output/stage_2_output.csv')
        outreach_df = pd.read_csv('inputs/outreach.csv')
        salesforce_df = pd.read_csv('inputs/salesforce.csv')
        
        # Validate required columns
        required_columns = {
            'stage2_df': ['Account Name'],
            'outreach_df': ['Account: Account Name', 'Date', 'Call Duration', 'Call Result', 'Comments'],
            'salesforce_df': ['Account Name']
        }
        
        for df_name, cols in required_columns.items():
            df = locals()[df_name]
            missing_cols = [col for col in cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns in {df_name}: {missing_cols}")
        
        # Merge datasets
        # First merge stage 2 with Salesforce
        combined_df = pd.merge(
            stage2_df,
            salesforce_df,
            on='Account Name',
            how='left'
        )
        
        # Then merge with outreach
        combined_df = pd.merge(
            combined_df,
            outreach_df,
            left_on='Account Name',
            right_on='Account: Account Name',
            how='left'
        )
        
        # Process accounts
        account_groups = list(combined_df.groupby('Account Name'))
        results = []
        
        for account_data in account_groups:
            results.append(process_account(account_data))
        
        # Create results DataFrame
        results_df = pd.DataFrame(results)
        
        # Save results
        output_path = 'output/stage_3_output.csv'
        results_df.to_csv(output_path, index=False)
        
        # Generate summary report
        generate_summary_report(results_df)
        
        logger.info(f"Stage 3 processing complete. Results saved to {output_path}")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 