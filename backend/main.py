from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from backend.config import config
from backend.models import Card, TopicFeedResponse, MorningBriefResponse
from backend.database import db_manager
from backend.vector_store import vector_store
from backend.summarizer import summarizer
from backend.scheduler import daily_scheduler

# Create FastAPI app
app = FastAPI(
    title="AI Flash Cards API",
    description="Lightning-fast AI insights, sourced fresh daily",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(level=getattr(logging, "INFO"))
logger = logging.getLogger(__name__)

# ============================================================================
# CORE API ENDPOINTS
# ============================================================================

@app.get("/api/morning-brief", response_model=MorningBriefResponse)
async def get_morning_brief():
    """Get the daily Morning Brief with top N articles"""
    try:
        # Get recent articles (last 7 days, top N)
        articles = db_manager.get_recent_articles(
            limit=config.morning_brief_top_n,
            days=7
        )
        
        # If we don't have enough articles in the last 7 days, fill with older articles
        # Exclude Hacker News only in the last resort tier (raw articles)
        if len(articles) < config.morning_brief_top_n:
            # Get additional articles without date restriction, exclude HN in last resort
            additional_articles = db_manager.get_recent_articles(
                limit=config.morning_brief_top_n - len(articles),
                days=None,
                exclude_hacker_news=True  # Filter HN only in last resort tier
            )
            # Deduplicate by content_id and combine
            existing_ids = {a.content_id for a in articles}
            for article in additional_articles:
                if article.content_id not in existing_ids:
                    articles.append(article)
                    if len(articles) >= config.morning_brief_top_n:
                        break
        
        return MorningBriefResponse(
            items=articles[:config.morning_brief_top_n],
            total_count=len(articles)
        )
        
    except Exception as e:
        logger.error(f"Error getting morning brief: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve morning brief")

@app.get("/api/topic-feed", response_model=TopicFeedResponse)
async def get_topic_feed(
    q: str = Query(..., description="Search query"),
    timeframe: str = Query("all", description="Timeframe: 24h, 7d, 30d, all")
):
    """Get topic-based feed with semantic search"""
    try:
        # Validate timeframe
        timeframe_days = None
        if timeframe == "24h":
            timeframe_days = 1
        elif timeframe == "7d":
            timeframe_days = 7
        elif timeframe == "30d":
            timeframe_days = 30
        elif timeframe == "all":
            timeframe_days = None
        else:
            raise HTTPException(status_code=400, detail="Invalid timeframe. Use: 24h, 7d, 30d, all")
        
        # Try vector search first with timeout, fallback to database search
        print(f"Attempting vector search for: {q} (with 2.5s timeout)")
        search_results = []
        
        try:
            # Run vector search in thread pool with timeout (2.5 seconds)
            # This prevents blocking and allows fast fallback
            try:
                # Use asyncio.to_thread if available (Python 3.9+), otherwise use run_in_executor
                try:
                    vector_results = await asyncio.wait_for(
                        asyncio.to_thread(
                            vector_store.semantic_search,
                            q,
                            config.topic_feed_top_k,
                            timeframe_days
                        ),
                        timeout=2.5  # 2.5 second timeout
                    )
                except AttributeError:
                    # Fallback for Python < 3.9
                    loop = asyncio.get_event_loop()
                    executor = ThreadPoolExecutor(max_workers=1)
                    vector_results = await asyncio.wait_for(
                        loop.run_in_executor(
                            executor,
                            vector_store.semantic_search,
                            q,
                            config.topic_feed_top_k,
                            timeframe_days
                        ),
                        timeout=2.5  # 2.5 second timeout
                    )
                
                print(f"Vector search completed in time, returned {len(vector_results)} results")
                
                if vector_results:
                    # Convert vector search results to Card objects
                    for i, result in enumerate(vector_results):
                        try:
                            # Create Card object from vector search result
                            from backend.models import Reference
                            # Ensure required string fields are not None
                            tl_dr = result.get('tl_dr') or ''
                            why_it_matters = result.get('why_it_matters') or ''
                            summary = result.get('summary') or ''
                            title = result.get('title') or ''
                            
                            card = Card(
                                content_id=result.get('content_id', ''),
                                type=result.get('type', 'blog'),
                                title=title,
                                source=result.get('source', ''),
                                published_at=datetime.fromisoformat(result.get('published_at', '').replace('Z', '+00:00')),
                                tl_dr=tl_dr,
                                summary=summary,
                                why_it_matters=why_it_matters,
                                tags=result.get('tags', []) or [],
                                badges=result.get('badges', []) or [],
                                references=[Reference(**ref) for ref in result.get('references', []) or []],
                                snippet=result.get('snippet') or None,
                                synthesis_failed=result.get('synthesis_failed', False)
                            )
                            search_results.append(card)
                        except Exception as card_error:
                            print(f"Error converting result {i+1}: {card_error}")
                            continue
                    print(f"Converted to {len(search_results)} Card objects")
                else:
                    # No vector results, fallback to database search
                    print("No vector results, falling back to database search")
                    search_results = db_manager.search_articles(
                        query=q,
                        limit=config.topic_feed_top_k,
                        days=timeframe_days
                    )
                    print(f"Database search returned {len(search_results)} results")
                    
            except asyncio.TimeoutError:
                print(f"Vector search timed out after 2.5s, falling back to database search")
                # Immediately fallback to database search
                search_results = db_manager.search_articles(
                    query=q,
                    limit=config.topic_feed_top_k,
                    days=timeframe_days
                )
                print(f"Database search returned {len(search_results)} results")
                
        except Exception as e:
            print(f"Vector search failed: {e}, falling back to database search")
            # Fallback to database search
            try:
                search_results = db_manager.search_articles(
                    query=q,
                    limit=config.topic_feed_top_k,
                    days=timeframe_days
                )
                print(f"Database search returned {len(search_results)} results")
            except Exception as db_e:
                print(f"Database search also failed: {db_e}")
                search_results = []
        
        if not search_results:
            return TopicFeedResponse(
                topic_query=q,
                topic_summary=f"No recent articles found for '{q}'",
                why_it_matters="Try a different search term or broader timeframe",
                items=[],
                meta={
                    "generated_at": datetime.utcnow().isoformat(),
                    "timeframe": timeframe,
                    "results_count": 0
                }
            )
        
        # Search results are already Card objects from database search
        cards = search_results
        
        # Generate topic summary
        try:
            # Convert Card objects to dictionaries for the summarizer
            search_results_dicts = [card.model_dump() for card in search_results]
            topic_summary, why_it_matters = summarizer.generate_topic_summary(q, search_results_dicts)
        except Exception as e:
            logger.warning(f"Error generating topic summary: {e}")
            topic_summary = f"Recent developments in {q}"
            why_it_matters = "This topic is significant for AI research"
        
        return TopicFeedResponse(
            topic_query=q,
            topic_summary=topic_summary,
            why_it_matters=why_it_matters,
            items=cards,
            meta={
                "generated_at": datetime.utcnow().isoformat(),
                "timeframe": timeframe,
                "results_count": len(cards)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic feed: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve topic feed")

@app.get("/api/card/{content_id}", response_model=Card)
async def get_card_detail(content_id: str = Path(..., description="Content ID")):
    """Get detailed information for a specific card"""
    try:
        article = db_manager.get_article_by_id(content_id)
        if not article:
            raise HTTPException(status_code=404, detail="Card not found")
        
        return article
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting card detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve card detail")

# ============================================================================
# SYSTEM MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and statistics"""
    try:
        return daily_scheduler.get_status()
    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduler status")

@app.post("/api/scheduler/ingest")
async def trigger_ingestion():
    """Manually trigger ingestion job"""
    try:
        result = daily_scheduler.run_ingestion_now()
        return result
    except Exception as e:
        logger.error(f"Error triggering ingestion: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger ingestion")

@app.get("/api/scheduler/stats")
async def get_scheduler_stats():
    """Get ingestion statistics"""
    try:
        return daily_scheduler.get_ingestion_stats()
    except Exception as e:
        logger.error(f"Error getting scheduler stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scheduler statistics")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        article_count = db_manager.get_article_count()
        
        # Check recent articles
        recent_articles = db_manager.get_recent_articles(limit=1, days=1)
        has_recent_articles = len(recent_articles) > 0
        
        # Check scheduler status
        scheduler_status = daily_scheduler.get_status()
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": {
                "connected": True,
                "article_count": article_count
            },
            "recent_articles": has_recent_articles,
            "scheduler": scheduler_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

# ============================================================================
# FRONTEND SERVING
# ============================================================================

@app.get("/")
async def serve_frontend():
    """Serve the frontend application"""
    try:
        frontend_path = "frontend/index.html"
        if os.path.exists(frontend_path):
            return FileResponse(frontend_path)
        else:
            return {"message": "Frontend not found. Please check the build process."}
    except Exception as e:
        logger.error(f"Error serving frontend: {e}")
        return {"message": "Error serving frontend", "error": str(e)}

# Mount static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup event"""
    try:
        logger.info("Starting AI Flash Cards application...")
        
        # Start the scheduler
        daily_scheduler.start()
        logger.info("Scheduler started")
        
        # Log configuration
        logger.info(f"Database path: {config.database_path}")
        logger.info(f"RSS sources: 3")
        logger.info(f"Top N morning brief: {config.morning_brief_top_n}")
        
        logger.info("AI Flash Cards application started successfully")
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event"""
    try:
        logger.info("Shutting down AIFlash application...")
        
        # Stop the scheduler
        daily_scheduler.stop()
        logger.info("Scheduler stopped")
        
        logger.info("AIFlash application shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors"""
    return {"error": "Not found", "detail": str(exc)}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return {"error": "Internal server error", "detail": "An unexpected error occurred"}

# ============================================================================
# DEVELOPMENT ENDPOINTS (Remove in production)
# ============================================================================

@app.get("/api/dev/ingest")
async def dev_trigger_ingestion():
    """Development endpoint to trigger ingestion"""
    try:
        from backend.ingestion import ingestion_pipeline
        result = ingestion_pipeline.ingest_pipeline()
        return result
    except Exception as e:
        logger.error(f"Error in dev ingestion: {e}")
        raise HTTPException(status_code=500, detail=f"Dev ingestion failed: {str(e)}")

@app.get("/api/dev/stats")
async def dev_get_stats():
    """Development endpoint to get system statistics"""
    try:
        stats = {
            "database": {
                "article_count": db_manager.get_article_count(),
                "recent_articles_7d": len(db_manager.get_recent_articles(limit=1000, days=7))
            },
            "vector_store": {
                "document_count": vector_store.get_document_count()
            },
            "scheduler": daily_scheduler.get_status(),
            "config": {
                "rss_sources": 3,
                "top_n_morning_brief": config.morning_brief_top_n,
                "database_path": config.database_path
            }
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting dev stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dev stats: {str(e)}")

@app.post("/api/dev/reindex-vector-store")
async def dev_reindex_vector_store():
    """Development endpoint to re-index all summarized articles from database to vector store"""
    try:
        logger.info("Manual vector store re-indexing triggered via API")
        
        # Run re-indexing synchronously (it's already fast with small batches)
        result = vector_store.reindex_all_summarized_articles()
        
        return {
            "success": result.get('success', False),
            "message": result.get('message', 'Re-indexing completed'),
            "indexed": result.get('indexed', 0),
            "failed": result.get('failed', 0)
        }
    except Exception as e:
        logger.error(f"Error triggering re-indexing: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger re-indexing: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
