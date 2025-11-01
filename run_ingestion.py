#!/usr/bin/env python3
"""
Script to run the AIFlash ingestion pipeline
Includes all three phases: ingestion, relevance check, and summarization
"""
import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.ingestion import ingestion_pipeline

def main():
    """Run the complete ingestion pipeline including relevance check and summarization"""
    print("=" * 60)
    print("Starting Complete AIFlash Ingestion Pipeline")
    print("=" * 60)
    
    try:
        # Phase 1: Fetch and save raw articles
        print("\n" + "-" * 60)
        print("PHASE 1: Fetching and Saving Raw Articles")
        print("-" * 60)
        print("⚠️  NOTE: Database will be cleared before ingestion (fresh start)")
        result = ingestion_pipeline.ingest_pipeline(
            limit_per_feed=10,
            batch_size=None,  # Not used in new pipeline
            clear_db=True  # Clear database for fresh ingestion
        )
        
        print(f"\nPhase 1 Results:")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message']}")
        print(f"  Raw Articles Saved: {result.get('raw_articles_saved', result.get('new_articles', 0))}")
        print(f"  Total Articles: {result['total_articles']}")
        
        if not result['success']:
            print("\n❌ Phase 1 failed, but continuing with next phases...")
        
        # Phase 2: Relevance Check
        print("\n" + "-" * 60)
        print("PHASE 2: Relevance Check")
        print("-" * 60)
        relevance_result = ingestion_pipeline.run_relevance_check_job(batch_size=10)
        
        print(f"\nPhase 2 Results:")
        print(f"  Success: {relevance_result['success']}")
        print(f"  Message: {relevance_result['message']}")
        print(f"  Articles Checked: {relevance_result.get('checked', 0)}")
        print(f"  Relevant Articles: {relevance_result.get('relevant', 0)}")
        
        if not relevance_result['success']:
            print("\n⚠️  Phase 2 failed, but continuing with next phase...")
        
        # Phase 3: Summarization
        print("\n" + "-" * 60)
        print("PHASE 3: Summarization")
        print("-" * 60)
        summary_result = ingestion_pipeline.run_summarization_job(limit=20)
        
        print(f"\nPhase 3 Results:")
        print(f"  Success: {summary_result['success']}")
        print(f"  Message: {summary_result['message']}")
        print(f"  Articles Summarized: {summary_result.get('summarized', 0)}")
        print(f"  Failed: {summary_result.get('failed', 0)}")
        print(f"  Vector Store Success: {summary_result.get('vector_store_success', False)}")
        
        if not summary_result['success']:
            print("\n⚠️  Phase 3 failed!")
        
        # Final Summary
        print("\n" + "=" * 60)
        print("Complete Pipeline Summary")
        print("=" * 60)
        print(f"✅ Raw Articles Saved: {result.get('raw_articles_saved', result.get('new_articles', 0))}")
        print(f"✅ Articles Checked for Relevance: {relevance_result.get('checked', 0)}")
        print(f"✅ Relevant Articles Found: {relevance_result.get('relevant', 0)}")
        print(f"✅ Articles Summarized: {summary_result.get('summarized', 0)}")
        print(f"❌ Summarization Failures: {summary_result.get('failed', 0)}")
        print(f"📊 Total Articles in Database: {result['total_articles']}")
        
        if result['success'] and relevance_result['success'] and summary_result['success']:
            print("\n✅ Complete pipeline finished successfully!")
            return 0
        else:
            print("\n⚠️  Pipeline completed with some failures (check logs above)")
            return 1
        
    except Exception as e:
        print(f"\n❌ Error running ingestion pipeline: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
