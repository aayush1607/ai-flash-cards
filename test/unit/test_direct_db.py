#!/usr/bin/env python3
"""
Test direct database access to see if articles are available
"""
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.database import db_manager
from backend.models import Card

def test_database():
    """Test direct database access"""
    print("Testing database access...")
    
    try:
        # Get article count
        count = db_manager.get_article_count()
        print(f"Total articles in database: {count}")
        
        # Get recent articles
        articles = db_manager.get_recent_articles(limit=5, days=30)
        print(f"Recent articles: {len(articles)}")
        
        for i, article in enumerate(articles):
            print(f"{i+1}. {article.title}")
            print(f"   Source: {article.source}")
            print(f"   Published: {article.published_at}")
            print(f"   Summary: {article.summary[:100]}...")
            print()
        
        return True
        
    except Exception as e:
        print(f"Error accessing database: {e}")
        return False

if __name__ == "__main__":
    success = test_database()
    sys.exit(0 if success else 1)
