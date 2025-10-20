#!/usr/bin/env python3
"""
Script to run the AIFlash ingestion pipeline
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ingestion import RSSIngestionPipeline

def main():
    """Run the ingestion pipeline"""
    print("Starting AIFlash data ingestion...")
    
    try:
        # Create ingestion pipeline
        pipeline = RSSIngestionPipeline()
        
        # Run the ingestion with limit of 1 article per feed, batch filtering, and clear database
        print("Fetching articles from RSS feeds (limit: 5 per feed)...")
        print("WARNING: CLEARING DATABASE - All existing articles will be removed!")
        result = pipeline.ingest_pipeline(limit_per_feed=5, batch_size=5, clear_db=True)
        
        print(f"Ingestion completed successfully! Result: {result}")
        
    except Exception as e:
        print(f"Error during ingestion: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
