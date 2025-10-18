# Todo 11: Error Handling and Fallback Mechanisms

## Objective
Implement comprehensive error handling and fallback mechanisms across the entire application to ensure graceful degradation and user-friendly error experiences.

## Files to Update

### 1. `backend/main.py` - Enhanced Error Handling
Add comprehensive error handling to the FastAPI application:

```python
# Add to existing main.py

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import traceback
from typing import Union

# ============================================================================
# ENHANCED ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with detailed logging"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Request failed",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with helpful messages"""
    logger.error(f"Validation error: {exc.errors()} - Path: {request.url.path}")
    
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation failed",
            "detail": exc.errors(),
            "status_code": 422,
            "path": request.url.path
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with fallback responses"""
    logger.error(f"Unexpected error: {str(exc)} - Path: {request.url.path}")
    logger.error(f"Traceback: {traceback.format_exc()}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
            "path": request.url.path
        }
    )

# ============================================================================
# ENHANCED API ENDPOINTS WITH ERROR HANDLING
# ============================================================================

@app.get("/api/morning-brief", response_model=MorningBriefResponse)
async def get_morning_brief():
    """Get the daily Morning Brief with comprehensive error handling"""
    try:
        # Get recent articles with fallback
        articles = []
        try:
            articles = db_manager.get_recent_articles(
                limit=config.app.top_n_morning_brief,
                days=7
            )
        except Exception as db_error:
            logger.warning(f"Database error, trying fallback: {db_error}")
            # Fallback to any recent articles
            try:
                articles = db_manager.get_recent_articles(
                    limit=config.app.top_n_morning_brief,
                    days=None
                )
            except Exception as fallback_error:
                logger.error(f"Fallback database error: {fallback_error}")
                # Return empty response with error indicator
                return MorningBriefResponse(
                    items=[],
                    total_count=0,
                    error="Database temporarily unavailable"
                )
        
        if not articles:
            logger.warning("No articles found for morning brief")
            return MorningBriefResponse(
                items=[],
                total_count=0,
                warning="No recent articles available"
            )
        
        return MorningBriefResponse(
            items=articles,
            total_count=len(articles)
        )
        
    except Exception as e:
        logger.error(f"Error getting morning brief: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve morning brief. Please try again later."
        )

@app.get("/api/topic-feed", response_model=TopicFeedResponse)
async def get_topic_feed(
    q: str = Query(..., description="Search query"),
    timeframe: str = Query("30d", description="Timeframe: 24h, 7d, 30d, all")
):
    """Get topic-based feed with comprehensive error handling"""
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
            raise HTTPException(
                status_code=400, 
                detail="Invalid timeframe. Use: 24h, 7d, 30d, all"
            )
        
        # Perform semantic search with fallback
        search_results = []
        try:
            search_results = vector_store.semantic_search(
                query=q,
                top_k=15,
                days=timeframe_days
            )
        except Exception as search_error:
            logger.warning(f"Vector search failed, trying database search: {search_error}")
            # Fallback to database search
            try:
                search_results = db_manager.search_articles(
                    query=q,
                    limit=15,
                    days=timeframe_days
                )
                # Convert to search result format
                search_results = [
                    {
                        "content_id": article.content_id,
                        "title": article.title,
                        "summary": article.summary,
                        "source": article.source,
                        "type": article.type,
                        "published_at": article.published_at.isoformat(),
                        "tags": article.tags,
                        "badges": article.badges,
                        "snippet": article.snippet or "",
                        "score": 1.0
                    }
                    for article in search_results
                ]
            except Exception as db_error:
                logger.error(f"Database search also failed: {db_error}")
                return TopicFeedResponse(
                    topic_query=q,
                    topic_summary=f"Search temporarily unavailable for '{q}'",
                    why_it_matters="Please try again later or use a different search term",
                    items=[],
                    meta={
                        "generated_at": datetime.utcnow().isoformat(),
                        "timeframe": timeframe,
                        "results_count": 0,
                        "error": "Search service unavailable"
                    }
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
                article = db_manager.get_article_by_id(result['content_id'])
                if article:
                    cards.append(article)
            except Exception as e:
                logger.warning(f"Error retrieving article {result['content_id']}: {e}")
                continue
        
        # Generate topic summary with fallback
        try:
            topic_summary, why_it_matters = summarizer.generate_topic_summary(q, search_results)
        except Exception as summary_error:
            logger.warning(f"Topic summary generation failed: {summary_error}")
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
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail="Failed to retrieve topic feed. Please try again later."
        )

# ============================================================================
# ENHANCED HEALTH CHECK
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Enhanced health check with detailed diagnostics"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {}
        }
        
        # Check database
        try:
            article_count = db_manager.get_article_count()
            recent_articles = db_manager.get_recent_articles(limit=1, days=1)
            health_status["services"]["database"] = {
                "status": "healthy",
                "article_count": article_count,
                "recent_articles": len(recent_articles) > 0
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check vector store
        try:
            # Simple test query
            test_results = vector_store.semantic_search("test", top_k=1)
            health_status["services"]["vector_store"] = {
                "status": "healthy",
                "test_results": len(test_results)
            }
        except Exception as e:
            health_status["services"]["vector_store"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check scheduler
        try:
            scheduler_status = daily_scheduler.get_status()
            health_status["services"]["scheduler"] = {
                "status": "healthy",
                "running": scheduler_status["running"],
                "last_run": scheduler_status["last_run"]
            }
        except Exception as e:
            health_status["services"]["scheduler"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check Azure OpenAI
        try:
            # Simple test embedding
            test_embedding = summarizer.embed_text("test")
            health_status["services"]["azure_openai"] = {
                "status": "healthy",
                "embedding_dimensions": len(test_embedding)
            }
        except Exception as e:
            health_status["services"]["azure_openai"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }
```

### 2. `frontend/app.js` - Enhanced Error Handling
Add comprehensive error handling to the frontend:

```javascript
// Add to existing AIFlashApp class

class AIFlashApp {
    constructor() {
        this.currentCards = [];
        this.currentIndex = 0;
        this.isTopicView = false;
        this.currentTopic = '';
        this.currentTimeframe = '30d';
        this.isLoading = false;
        this.retryCount = 0;
        this.maxRetries = 3;
        this.retryDelay = 1000; // 1 second
        
        // Initialize the application
        this.init();
    }

    // Enhanced error handling methods
    async handleApiError(error, context = '') {
        console.error(`API Error in ${context}:`, error);
        
        // Determine error type and user message
        let userMessage = 'Something went wrong. Please try again.';
        let canRetry = true;
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            userMessage = 'Network error. Please check your connection.';
        } else if (error.message.includes('404')) {
            userMessage = 'Content not found.';
            canRetry = false;
        } else if (error.message.includes('500')) {
            userMessage = 'Server error. Please try again later.';
        } else if (error.message.includes('timeout')) {
            userMessage = 'Request timed out. Please try again.';
        }
        
        // Show error with retry option
        this.showError(userMessage, canRetry);
        
        // Log error for debugging
        this.logError(error, context);
    }

    logError(error, context) {
        const errorLog = {
            timestamp: new Date().toISOString(),
            context: context,
            error: {
                name: error.name,
                message: error.message,
                stack: error.stack
            },
            userAgent: navigator.userAgent,
            url: window.location.href
        };
        
        // In production, you might want to send this to a logging service
        console.error('Error Log:', errorLog);
    }

    async loadMorningBrief() {
        try {
            this.showLoading();
            this.isLoading = true;
            this.retryCount = 0;

            const response = await this.fetchWithRetry('/api/morning-brief');
            const data = await response.json();

            this.currentCards = data.items || [];
            this.currentIndex = 0;
            this.isTopicView = false;

            if (this.currentCards.length === 0) {
                this.showEmpty('No articles available. Check back later for new content.');
            } else {
                this.renderCurrentCard();
                this.hideLoading();
            }

        } catch (error) {
            await this.handleApiError(error, 'loadMorningBrief');
        } finally {
            this.isLoading = false;
        }
    }

    async handleSearch() {
        const searchInput = document.getElementById('searchInput');
        const query = searchInput.value.trim();

        if (!query) {
            this.showError('Please enter a search term.');
            return;
        }

        try {
            this.showLoading();
            this.isLoading = true;
            this.retryCount = 0;

            const response = await this.fetchWithRetry(
                `/api/topic-feed?q=${encodeURIComponent(query)}&timeframe=${this.currentTimeframe}`
            );
            const data = await response.json();

            this.currentCards = data.items || [];
            this.currentIndex = 0;
            this.isTopicView = true;
            this.currentTopic = query;

            // Show topic header
            this.showTopicHeader(data);

            if (this.currentCards.length === 0) {
                this.showEmpty(`No articles found for "${query}". Try a different search term.`);
            } else {
                this.renderCurrentCard();
                this.hideLoading();
            }

        } catch (error) {
            await this.handleApiError(error, 'handleSearch');
        } finally {
            this.isLoading = false;
        }
    }

    async fetchWithRetry(url, options = {}) {
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
                
                const response = await fetch(url, {
                    ...options,
                    signal: controller.signal
                });
                
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return response;
                
            } catch (error) {
                this.retryCount = attempt + 1;
                
                if (attempt === this.maxRetries - 1) {
                    throw error;
                }
                
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, this.retryDelay * (attempt + 1)));
            }
        }
    }

    showError(message, canRetry = true) {
        const errorMessage = document.getElementById('errorMessage');
        const retryBtn = document.getElementById('retryBtn');
        
        errorMessage.textContent = message;
        
        if (canRetry) {
            retryBtn.style.display = 'inline-block';
        } else {
            retryBtn.style.display = 'none';
        }
        
        document.getElementById('errorState').classList.remove('hidden');
        this.hideAllStates();
    }

    showEmpty(message = 'No content available.') {
        const emptyState = document.getElementById('emptyState');
        const emptyMessage = emptyState.querySelector('p');
        emptyMessage.textContent = message;
        emptyState.classList.remove('hidden');
        this.hideAllStates();
    }

    async retry() {
        if (this.isTopicView) {
            await this.handleSearch();
        } else {
            await this.loadMorningBrief();
        }
    }

    // Enhanced status indicator
    async updateStatusIndicator() {
        const indicator = document.getElementById('statusIndicator');
        const statusText = indicator.nextElementSibling;

        try {
            const response = await fetch('/api/health', { timeout: 5000 });
            const data = await response.json();
            
            if (data.status === 'healthy') {
                indicator.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
                statusText.textContent = 'Live';
            } else if (data.status === 'degraded') {
                indicator.className = 'w-3 h-3 bg-yellow-500 rounded-full animate-pulse';
                statusText.textContent = 'Issues';
            } else {
                indicator.className = 'w-3 h-3 bg-red-500 rounded-full animate-pulse';
                statusText.textContent = 'Offline';
            }
        } catch (error) {
            indicator.className = 'w-3 h-3 bg-red-500 rounded-full animate-pulse';
            statusText.textContent = 'Offline';
        }
    }

    // Enhanced card rendering with error handling
    renderCard(card) {
        try {
            // Basic information
            document.getElementById('cardSource').textContent = card.source || 'Unknown Source';
            document.getElementById('cardDate').textContent = this.formatDate(card.published_at);
            document.getElementById('cardTitle').textContent = card.title || 'Untitled';
            document.getElementById('cardTldr').textContent = card.tl_dr || 'Summary not available';
            document.getElementById('cardSummary').textContent = card.summary || 'Content summary not available';
            document.getElementById('cardWhy').textContent = card.why_it_matters || 'Significance not determined';

            // Synthesis warning
            const synthesisWarning = document.getElementById('synthesisWarning');
            if (card.synthesis_failed) {
                synthesisWarning.classList.remove('hidden');
            } else {
                synthesisWarning.classList.add('hidden');
            }

            // Badges
            this.renderBadges(card.badges || []);

            // Tags
            this.renderTags(card.tags || []);

            // References
            this.renderReferences(card.references || []);

            // Show card
            document.getElementById('currentCard').classList.remove('hidden');
            document.getElementById('cardNavigation').classList.remove('hidden');
            
        } catch (error) {
            console.error('Error rendering card:', error);
            this.showError('Error displaying content. Please try again.');
        }
    }

    // Enhanced reference rendering with error handling
    renderReferences(references) {
        const referencesContainer = document.getElementById('cardReferences');
        referencesContainer.innerHTML = '';

        if (!references || references.length === 0) {
            const noRefs = document.createElement('div');
            noRefs.className = 'text-white/60 text-sm';
            noRefs.textContent = 'No references available';
            referencesContainer.appendChild(noRefs);
            return;
        }

        references.forEach(ref => {
            try {
                const refElement = document.createElement('a');
                refElement.href = ref.url || '#';
                refElement.target = '_blank';
                refElement.rel = 'noopener noreferrer';
                refElement.className = 'px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors border border-white/20 text-sm';
                refElement.textContent = ref.label || 'Reference';
                
                // Add error handling for broken links
                refElement.addEventListener('click', (e) => {
                    if (!ref.url || ref.url === '#') {
                        e.preventDefault();
                        this.showError('Reference link not available');
                    }
                });
                
                referencesContainer.appendChild(refElement);
            } catch (error) {
                console.error('Error rendering reference:', error);
            }
        });
    }
}
```

## Key Features to Implement

### 1. Backend Error Handling
- **HTTP Exception Handling**: Proper HTTP status codes
- **Validation Error Handling**: Clear validation messages
- **Database Fallbacks**: Alternative data sources
- **Service Degradation**: Graceful service degradation
- **Comprehensive Logging**: Detailed error logging

### 2. Frontend Error Handling
- **Network Error Handling**: Connection and timeout errors
- **Retry Logic**: Automatic retry with exponential backoff
- **User-Friendly Messages**: Clear error messages
- **Fallback Content**: Show partial data when possible
- **Error Logging**: Client-side error tracking

### 3. Service Degradation
- **Database Fallbacks**: Use cached data when possible
- **Search Fallbacks**: Database search when vector search fails
- **Content Fallbacks**: Show basic content when AI fails
- **Status Indicators**: Show service health status

### 4. Error Recovery
- **Automatic Retry**: Retry failed operations
- **Manual Retry**: User-initiated retry
- **State Recovery**: Reset to known good state
- **Graceful Degradation**: Continue with limited functionality

## Error Types and Handling

### 1. Network Errors
- **Connection Timeout**: Retry with backoff
- **DNS Resolution**: Clear error message
- **SSL/TLS Errors**: Security warnings
- **Rate Limiting**: Wait and retry

### 2. API Errors
- **400 Bad Request**: Validation error messages
- **404 Not Found**: Content not found
- **500 Server Error**: Server-side error handling
- **503 Service Unavailable**: Service degradation

### 3. Data Errors
- **Missing Data**: Fallback to defaults
- **Invalid Data**: Data validation and cleaning
- **Corrupted Data**: Skip and continue
- **Empty Results**: Show appropriate messages

## Fallback Strategies

### 1. Data Fallbacks
- **Cached Data**: Use previously loaded data
- **Default Content**: Show placeholder content
- **Partial Data**: Show available information
- **Error Messages**: Clear error communication

### 2. Service Fallbacks
- **Database Search**: When vector search fails
- **Basic Summarization**: When AI fails
- **Static Content**: When dynamic content fails
- **Offline Mode**: Limited functionality

### 3. User Experience Fallbacks
- **Loading States**: Show progress indicators
- **Error States**: Clear error messages
- **Empty States**: Helpful empty state messages
- **Retry Options**: Manual retry capabilities

## Validation Checklist
- [ ] All API endpoints have proper error handling
- [ ] Frontend handles all error scenarios gracefully
- [ ] Retry logic works for transient failures
- [ ] Fallback mechanisms provide useful content
- [ ] Error messages are user-friendly and actionable
- [ ] Logging provides useful debugging information
- [ ] Service degradation is handled gracefully
- [ ] Network errors are handled appropriately
- [ ] Data validation prevents invalid states
- [ ] Recovery mechanisms work correctly

## Next Steps
After completing this todo, proceed to "12-testing-validation" to implement comprehensive testing and validation of all application features.
