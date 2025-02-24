"""
Stage 2 Account Status Processor

This script processes the output from stage 1 and cross-references it with outreach data
to determine the current status of each account. It specifically looks for accounts that
have been marked as "Closed - Currently Not Interested" in the outreach data.

Key Features:
- Parallel processing of accounts for improved performance
- Tracks the most recent status for each account
- Captures closure dates and reasons
- Provides summary statistics

Input Files:
- output/stage_1_output.csv: Contains the stage 1 processed data
- outreach.csv: Contains the outreach history and status for accounts

Output:
- output/stage_2_output.csv: Stage 1 data enhanced with closure status information
    Additional columns:
    - Is Closed: Boolean indicating if account is closed
    - Close Date: Date when the account was marked as closed
    - Close Reason: Reason provided for closure

Usage:
    python scripts/stage_2_account_status.py

Requirements:
    - pandas
    - concurrent.futures (standard library)
    - logging (standard library)
"""

import pandas as pd
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_date(date_str: str) -> datetime:
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str (str): Date string in format 'MM/DD/YYYY'
        
    Returns:
        datetime: Parsed datetime object or None if parsing fails
    """
    try:
        return datetime.strptime(date_str, '%m/%d/%Y')
    except (ValueError, TypeError):
        return None

def process_account(account_data: Tuple[str, pd.DataFrame]) -> Dict:
    """
    Process outreach data for a single account to determine its current status.
    
    Args:
        account_data (Tuple[str, pd.DataFrame]): Tuple containing:
            - Account name (str)
            - DataFrame of outreach records for the account
            
    Returns:
        Dict: Account status information containing:
            - Account Name: Name of the account
            - Is Closed: Boolean indicating if account is closed
            - Close Date: Date when account was closed (if applicable)
            - Close Reason: Reason for closure (if applicable)
    """
    account_name, group = account_data
    
    # Sort by date to get most recent status
    group['Date'] = pd.to_datetime(group['Date'], format='%m/%d/%Y', errors='coerce')
    latest_entries = group.sort_values('Date', ascending=False)
    
    # Check if any recent entries are marked as closed
    is_closed = any(latest_entries['Call Result'].str.contains('Closed - Currently Not Interested', na=False))
    
    # Get the latest date and reason if closed
    if is_closed:
        latest_closed = latest_entries[
            latest_entries['Call Result'].str.contains('Closed - Currently Not Interested', na=False)
        ].iloc[0]
        
        close_date = latest_closed['Date']
        close_reason = latest_closed['Comments'] if pd.notna(latest_closed['Comments']) else "No reason provided"
    else:
        close_date = None
        close_reason = None
        
    return {
        'Account Name': account_name,
        'Is Closed': is_closed,
        'Close Date': close_date,
        'Close Reason': close_reason
    }

def main():
    """
    Main execution function that:
    1. Reads input files
    2. Processes account data in parallel
    3. Merges results with stage 1 data
    4. Saves enhanced dataset
    5. Prints summary statistics
    
    The function uses parallel processing to improve performance when dealing
    with large numbers of accounts. Error handling ensures graceful failure
    and logging provides visibility into the process.
    """
    try:
        logger.info("Starting stage 2 processing...")
        
        # Read the input files
        stage1_df = pd.read_csv('output/stage_1_output.csv')
        outreach_df = pd.read_csv('input/outreach.csv')
        
        # Clean up account names (remove leading/trailing whitespace)
        stage1_df['Account Name'] = stage1_df['Account Name'].str.strip()
        outreach_df['Account: Account Name'] = outreach_df['Account: Account Name'].str.strip()
        
        # Group outreach data by account name
        account_groups = list(outreach_df.groupby('Account: Account Name'))
        
        # Process accounts in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(process_account, account_groups))
        
        # Convert results to DataFrame
        status_df = pd.DataFrame(results)
        
        # Merge with stage 1 output
        final_df = pd.merge(
            stage1_df,
            status_df,
            on='Account Name',
            how='left'
        )
        
        # Fill NaN values
        final_df['Is Closed'] = final_df['Is Closed'].fillna(False)
        final_df['Close Reason'] = final_df['Close Reason'].fillna('N/A')
        
        # Save the results
        output_path = 'output/stage_2_output.csv'
        final_df.to_csv(output_path, index=False)
        logger.info(f"Stage 2 processing complete. Results saved to {output_path}")
        
        # Print summary statistics
        total_accounts = len(final_df)
        closed_accounts = final_df['Is Closed'].sum()
        logger.info(f"Total accounts processed: {total_accounts}")
        logger.info(f"Closed accounts: {closed_accounts}")
        logger.info(f"Closure rate: {(closed_accounts/total_accounts)*100:.2f}%")
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main() 