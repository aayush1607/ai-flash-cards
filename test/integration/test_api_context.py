#!/usr/bin/env python3
"""
Test API context database connection
"""
import sys
import os

# Simulate the API context
sys.path.append('backend')

from backend.config import config
from backend.database import db_manager

def test_api_context():
    """Test database in API context"""
    print(f"Current working directory: {os.getcwd()}")
    print(f"Database path: {config.database_path}")
    print(f"Database exists: {os.path.exists(config.database_path)}")
    
    # Try to find the database file
    if not os.path.exists(config.database_path):
        print("Database not found at expected path, searching...")
        for root, dirs, files in os.walk('.'):
            if 'aiflash.db' in files:
                print(f"Found database at: {os.path.join(root, 'aiflash.db')}")
                break
    
    try:
        # Test database connection
        count = db_manager.get_article_count()
        print(f"Article count: {count}")
        
        # Test search
        results = db_manager.search_articles('coffee', limit=5)
        print(f"Search results: {len(results)}")
        if results:
            print(f"First result: {results[0].title}")
        
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api_context()
