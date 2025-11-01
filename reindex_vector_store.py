#!/usr/bin/env python3
"""
Script to re-index all summarized articles from database to vector store.
This is useful when the vector store is empty or out of sync with the database.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.vector_store import vector_store
from backend.database import db_manager

def main():
    """Re-index all summarized articles to vector store"""
    print("=" * 60)
    print("Re-indexing Vector Store")
    print("=" * 60)
    print()
    
    # Check if index schema needs updating
    print("Checking index schema...")
    try:
        from backend.vector_store import vector_store
        existing_index = vector_store.index_client.get_index(vector_store.index_name)
        field_names = {field.name for field in existing_index.fields}
        required_fields = {'tl_dr', 'why_it_matters', 'references'}
        missing_fields = required_fields - field_names
        
        if missing_fields:
            print(f"[WARNING] Index is missing required fields: {missing_fields}")
            print("Azure Search doesn't support schema updates.")
            print("The index needs to be recreated with the new schema.")
            print()
            response = input("Do you want to recreate the index now? (yes/no): ")
            if response.lower() in ['yes', 'y']:
                if vector_store.recreate_index_with_schema():
                    print()
                    print("[SUCCESS] Index recreated. Continuing with re-indexing...")
                    print()
                else:
                    print("[ERROR] Failed to recreate index. Aborting.")
                    return 1
            else:
                print("Aborting. Please recreate the index first using:")
                print("  vector_store.recreate_index_with_schema()")
                return 1
        else:
            print("[SUCCESS] Index schema is up to date")
    except Exception as e:
        print(f"[INFO] Could not check index schema: {e}")
        print("Continuing with re-indexing...")
    
    print()
    
    # Check database status
    print("Checking database status...")
    total_articles = db_manager.get_article_count()
    
    with db_manager.get_session() as session:
        from backend.models import Article
        summarized_count = session.query(Article).filter(
            Article.is_summarized == True
        ).count()
    
    print(f"  Total articles in database: {total_articles}")
    print(f"  Summarized articles: {summarized_count}")
    print()
    
    # Check current vector store status
    print("Checking vector store status...")
    current_doc_count = vector_store.get_document_count()
    print(f"  Current documents in vector store: {current_doc_count}")
    print()
    
    if summarized_count == 0:
        print("[WARNING] No summarized articles found in database.")
        print("   Run processing/relevance check jobs first to summarize articles.")
        return 1
    
    # Re-index
    print("Starting re-indexing...")
    print("-" * 60)
    result = vector_store.reindex_all_summarized_articles()
    print("-" * 60)
    print()
    
    # Show results
    print("Re-indexing Results:")
    print(f"  Success: {result.get('success', False)}")
    print(f"  Indexed: {result.get('indexed', 0)}")
    print(f"  Failed: {result.get('failed', 0)}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print()
    
    # Verify
    new_doc_count = vector_store.get_document_count()
    print("Verification:")
    print(f"  Documents in vector store now: {new_doc_count}")
    
    if result.get('success') and new_doc_count > 0:
        print()
        print("[SUCCESS] Re-indexing completed successfully!")
        print(f"   Vector store now has {new_doc_count} documents.")
        return 0
    else:
        print()
        print("[WARNING] Re-indexing completed with issues.")
        print("   Check the logs above for details.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

