#!/usr/bin/env python3
"""
Test database path in API context
"""
import sys
import os
sys.path.append('backend')

from backend.config import config
from backend.database import db_manager

def test_db_path():
    """Test database path and connection"""
    print(f"Database path: {config.database_path}")
    print(f"Database exists: {os.path.exists(config.database_path)}")
    
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

if __name__ == "__main__":
    test_db_path()
