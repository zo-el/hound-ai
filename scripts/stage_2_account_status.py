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
import multiprocessing
from typing import Dict, List, Optional
import logging
from tqdm import tqdm
import os

# Configure logging
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

def process_account(account_data: tuple) -> Dict:
    """Process outreach data for a single account to determine its current status."""
    try:
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
    except Exception as e:
        logger.error(f"Error processing account {account_name}: {str(e)}")
        return None

def main():
    """Main execution function."""
    try:
        logger.info("\nStarting stage 2 processing...")
        
        # Define input/output paths
        stage1_path = 'output/stage_1_2_output.csv'
        outreach_path = 'inputs/outreach.csv'
        output_path = 'output/stage_2_output.csv'
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Validate input files exist
        if not os.path.exists(stage1_path):
            raise FileNotFoundError(f"Stage 1 output not found at: {stage1_path}")
        if not os.path.exists(outreach_path):
            raise FileNotFoundError(f"Outreach data not found at: {outreach_path}")
            
        logger.info("Reading input files...")
        stage1_df = pd.read_csv(stage1_path)
        outreach_df = pd.read_csv(outreach_path)
        
        # Clean up account names
        stage1_df['Account Name'] = stage1_df['Account Name'].str.strip()
        outreach_df['Account: Account Name'] = outreach_df['Account: Account Name'].str.strip()
        
        # Group outreach data by account name
        logger.info("Grouping accounts...")
        account_groups = list(outreach_df.groupby('Account: Account Name'))
        
        # Process accounts in parallel
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
        
        # Convert results to DataFrame
        logger.info("Compiling results...")
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
        logger.info(f"Saving results to {output_path}")
        final_df.to_csv(output_path, index=False)
        
        # Print summary statistics
        total_accounts = len(final_df)
        closed_accounts = final_df['Is Closed'].sum()
        logger.info("\nProcessing complete!")
        logger.info(f"Total accounts processed: {total_accounts}")
        logger.info(f"Closed accounts: {closed_accounts}")
        logger.info(f"Closure rate: {(closed_accounts/total_accounts)*100:.2f}%")
        
        # Verify output
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"Output file size: {file_size} bytes")
            
            # Print first few lines
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