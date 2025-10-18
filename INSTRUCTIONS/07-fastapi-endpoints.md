# Todo 7: FastAPI Application and Endpoints

## Objective
Create the FastAPI application with all required endpoints for Morning Brief, Topic Feed, and system management, including proper error handling and response formatting.

## Files to Create

### 1. `backend/main.py`
Create the complete FastAPI application:

```python
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
    title="AIFlash API",
    description="AI Flash — research-grade AI breakthroughs & model releases, fast.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORMMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup logging
logging.basicConfig(level=getattr(logging, config.app.log_level.upper()))
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
            limit=config.app.top_n_morning_brief,
            days=7
        )
        
        if not articles:
            # Fallback to any recent articles if none in last 7 days
            articles = db_manager.get_recent_articles(
                limit=config.app.top_n_morning_brief,
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
    timeframe: str = Query("30d", description="Timeframe: 24h, 7d, 30d, all")
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
        
        # Perform semantic search
        search_results = vector_store.semantic_search(
            query=q,
            top_k=15,
            days=timeframe_days
        )
        
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
        
        # Convert search results to Card objects
        cards = []
        for result in search_results:
            try:
                # Get full article from database
                article = db_manager.get_article_by_id(result['content_id'])
                if article:
                    cards.append(article)
            except Exception as e:
                logger.warning(f"Error retrieving article {result['content_id']}: {e}")
                continue
        
        # Generate topic summary
        try:
            topic_summary, why_it_matters = summarizer.generate_topic_summary(q, search_results)
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
        logger.info("Starting AIFlash application...")
        
        # Start the scheduler
        daily_scheduler.start()
        logger.info("Scheduler started")
        
        # Log configuration
        logger.info(f"Database path: {config.app.database_path}")
        logger.info(f"RSS sources: {len(config.app.rss_sources)}")
        logger.info(f"Top N morning brief: {config.app.top_n_morning_brief}")
        
        logger.info("AIFlash application started successfully")
        
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
                "rss_sources": len(config.app.rss_sources),
                "top_n_morning_brief": config.app.top_n_morning_brief,
                "database_path": config.app.database_path
            }
        }
        return stats
    except Exception as e:
        logger.error(f"Error getting dev stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get dev stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Key Features to Implement

### 1. Core API Endpoints
- **Morning Brief**: `/api/morning-brief` - Get daily top articles
- **Topic Feed**: `/api/topic-feed` - Semantic search with topic summarization
- **Card Detail**: `/api/card/{content_id}` - Individual card information
- **Health Check**: `/api/health` - System health monitoring

### 2. System Management
- **Scheduler Status**: `/api/scheduler/status` - Scheduler status and statistics
- **Manual Ingestion**: `/api/scheduler/ingest` - Trigger ingestion manually
- **Statistics**: `/api/scheduler/stats` - Detailed system statistics
- **Development Endpoints**: Dev-only endpoints for testing

### 3. Frontend Integration
- **Static File Serving**: Serve frontend files from `/frontend/` directory
- **Root Route**: Serve `index.html` at `/`
- **CORS Support**: Enable cross-origin requests for development
- **Error Handling**: Graceful error responses

### 4. Application Lifecycle
- **Startup**: Initialize scheduler and log configuration
- **Shutdown**: Stop scheduler gracefully
- **Error Recovery**: Handle startup/shutdown errors
- **Logging**: Comprehensive logging throughout

## API Response Formats

### 1. Morning Brief Response
```json
{
  "items": [
    {
      "content_id": "huggingface:abc123",
      "type": "blog",
      "title": "New Transformer Architecture",
      "source": "Hugging Face",
      "published_at": "2024-01-15T10:00:00Z",
      "tl_dr": "Novel transformer design reduces parameters by 50%",
      "summary": "This paper introduces a new transformer architecture...",
      "why_it_matters": "Enables more efficient AI models",
      "badges": ["CODE", "DATA"],
      "tags": ["transformer", "efficiency"],
      "references": [
        {"label": "Paper", "url": "https://arxiv.org/..."},
        {"label": "Code", "url": "https://github.com/..."}
      ],
      "snippet": "The new architecture uses grouped attention...",
      "synthesis_failed": false
    }
  ],
  "generated_at": "2024-01-15T10:00:00Z",
  "total_count": 10
}
```

### 2. Topic Feed Response
```json
{
  "topic_query": "transformer efficiency",
  "topic_summary": "Recent research focuses on reducing transformer complexity through grouped attention and dynamic sparsity.",
  "why_it_matters": "These advances enable more efficient AI models for edge deployment.",
  "items": [...],
  "meta": {
    "generated_at": "2024-01-15T10:00:00Z",
    "timeframe": "30d",
    "results_count": 8
  }
}
```

## Error Handling Strategy

### 1. HTTP Status Codes
- **200**: Success
- **400**: Bad request (invalid parameters)
- **404**: Not found (card not found)
- **500**: Internal server error

### 2. Error Response Format
```json
{
  "error": "Error type",
  "detail": "Detailed error message"
}
```

### 3. Logging Levels
- **INFO**: Normal operations
- **WARNING**: Non-critical issues
- **ERROR**: System errors
- **DEBUG**: Detailed debugging

## Validation Checklist
- [ ] All API endpoints return correct response models
- [ ] Error handling works for various failure scenarios
- [ ] CORS middleware allows frontend requests
- [ ] Static file serving works correctly
- [ ] Scheduler integration functions properly
- [ ] Health check provides useful system information
- [ ] Development endpoints work for testing
- [ ] Application lifecycle events work correctly
- [ ] Logging provides useful debugging information
- [ ] API documentation is accessible at `/api/docs`

## Next Steps
After completing this todo, proceed to "08-frontend-html" to build the frontend HTML structure.
