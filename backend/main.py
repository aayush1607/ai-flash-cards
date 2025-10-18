from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging
import os

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
        
        if not articles:
            # Fallback to any recent articles if none in last 7 days
            articles = db_manager.get_recent_articles(
                limit=config.morning_brief_top_n,
                days=None
            )
        
        return MorningBriefResponse(
            items=articles,
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
        
        # Try vector search first, fallback to database search
        print(f"Using vector search for: {q}")
        try:
            # Use vector search
            vector_results = vector_store.semantic_search(
                query=q,
                top_k=config.topic_feed_top_k,
                days=timeframe_days
            )
            print(f"Vector search returned {len(vector_results)} results")
            
            if vector_results:
                # Convert vector search results to Card objects
                search_results = []
                for i, result in enumerate(vector_results):
                    try:
                        # Create Card object from vector search result
                        from backend.models import Card, Reference
                        card = Card(
                            content_id=result.get('content_id', ''),
                            type=result.get('type', 'blog'),
                            title=result.get('title', ''),
                            source=result.get('source', ''),
                            published_at=datetime.fromisoformat(result.get('published_at', '').replace('Z', '+00:00')),
                            tl_dr=result.get('tl_dr', ''),
                            summary=result.get('summary', ''),
                            why_it_matters=result.get('why_it_matters', ''),
                            tags=result.get('tags', []),
                            badges=result.get('badges', []),
                            references=[Reference(**ref) for ref in result.get('references', [])],
                            snippet=result.get('snippet', ''),
                            synthesis_failed=result.get('synthesis_failed', False)
                        )
                        search_results.append(card)
                        print(f"Successfully converted result {i+1}: {card.title}")
                    except Exception as card_error:
                        print(f"Error converting result {i+1}: {card_error}")
                        print(f"Result data: {result}")
                        continue
                print(f"Converted to {len(search_results)} Card objects")
            else:
                search_results = []
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
            search_results_dicts = [card.dict() for card in search_results]
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
