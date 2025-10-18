# Todo 5: RSS Ingestion Pipeline

## Objective
Build a comprehensive RSS ingestion pipeline that fetches content from multiple sources, processes articles through AI summarization, and stores them in both SQLite and Azure AI Search.

## Files to Create

### 1. `backend/ingestion.py`
Create the complete ingestion pipeline:

```python
import feedparser
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import hashlib
import re
from backend.config import config
from backend.models import Card, Reference, generate_content_id, detect_content_type, extract_badges
from backend.database import db_manager
from backend.vector_store import vector_store
from backend.summarizer import summarizer

class RSSIngestionPipeline:
    """RSS ingestion and processing pipeline"""
    
    def __init__(self):
        self.rss_sources = config.app.rss_sources
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AIFlash/1.0 (AI Research Aggregator)'
        })
    
    def fetch_rss_feeds(self) -> List[Dict[str, Any]]:
        """Fetch and parse all RSS feeds"""
        all_articles = []
        
        for source_url in self.rss_sources:
            try:
                print(f"Fetching RSS feed: {source_url}")
                articles = self._fetch_single_feed(source_url)
                all_articles.extend(articles)
                print(f"Fetched {len(articles)} articles from {source_url}")
            except Exception as e:
                print(f"Error fetching {source_url}: {e}")
                continue
        
        return all_articles
    
    def _fetch_single_feed(self, feed_url: str) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed"""
        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                print(f"Warning: RSS feed {feed_url} has parsing issues")
            
            articles = []
            for entry in feed.entries:
                try:
                    article = self._parse_rss_entry(entry, feed_url)
                    if article:
                        articles.append(article)
                except Exception as e:
                    print(f"Error parsing entry: {e}")
                    continue
            
            return articles
            
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {e}")
            return []
    
    def _parse_rss_entry(self, entry: Any, source_url: str) -> Optional[Dict[str, Any]]:
        """Parse individual RSS entry"""
        try:
            # Extract basic information
            title = getattr(entry, 'title', '').strip()
            link = getattr(entry, 'link', '').strip()
            description = getattr(entry, 'description', '').strip()
            published = getattr(entry, 'published_parsed', None)
            
            if not title or not link:
                return None
            
            # Parse published date
            published_at = datetime.utcnow()
            if published:
                try:
                    published_at = datetime(*published[:6])
                except:
                    pass
            
            # Determine source name
            source_name = self._get_source_name(source_url, entry)
            
            # Extract content
            content = self._extract_content(entry)
            
            # Create article dictionary
            article = {
                'title': title,
                'link': link,
                'description': description,
                'content': content,
                'source': source_name,
                'published_at': published_at,
                'raw_entry': entry
            }
            
            return article
            
        except Exception as e:
            print(f"Error parsing RSS entry: {e}")
            return None
    
    def _get_source_name(self, feed_url: str, entry: Any) -> str:
        """Determine source name from feed URL and entry"""
        if 'huggingface.co' in feed_url:
            return 'Hugging Face'
        elif 'openai.com' in feed_url:
            return 'OpenAI'
        elif 'hnrss.org' in feed_url:
            return 'Hacker News'
        else:
            # Try to get from feed title or entry
            return getattr(entry, 'source', {}).get('title', 'Unknown Source')
    
    def _extract_content(self, entry: Any) -> str:
        """Extract full content from RSS entry"""
        # Try different content fields
        content_fields = ['content', 'summary', 'description', 'text']
        
        for field in content_fields:
            if hasattr(entry, field):
                content = getattr(entry, field)
                if isinstance(content, list) and content:
                    content = content[0].get('value', '')
                elif isinstance(content, str):
                    pass
                else:
                    continue
                
                if content and len(content) > 100:
                    return self._clean_content(content)
        
        # Fallback to description
        description = getattr(entry, 'description', '')
        if description:
            return self._clean_content(description)
        
        return ''
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize content"""
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        
        # Remove common RSS artifacts
        content = re.sub(r'Read more.*', '', content)
        content = re.sub(r'Continue reading.*', '', content)
        
        return content.strip()
    
    def process_article(self, raw_article: Dict[str, Any]) -> Optional[Card]:
        """Process raw article through AI pipeline"""
        try:
            # Generate content ID
            content_id = generate_content_id(
                raw_article['title'],
                raw_article['source'],
                raw_article['published_at']
            )
            
            # Detect content type
            content_type = detect_content_type(
                raw_article['link'],
                raw_article['title']
            )
            
            # Prepare content for summarization
            content_text = f"{raw_article['title']}\n\n{raw_article['content']}"
            if not content_text.strip():
                content_text = f"{raw_article['title']}\n\n{raw_article['description']}"
            
            # Summarize content
            try:
                tl_dr, summary, why_it_matters, tags, references = summarizer.summarize_content(
                    raw_article['title'],
                    content_text,
                    raw_article['source'],
                    raw_article['link']
                )
            except Exception as e:
                print(f"Error summarizing content: {e}")
                # Fallback to basic summarization
                tl_dr = raw_article['title'][:140]
                summary = raw_article['description'][:500] if raw_article['description'] else "Content summary not available."
                why_it_matters = "Research significance not determined."
                tags = []
                references = [Reference(label="Source", url=raw_article['link'])]
            
            # Extract badges
            badges = summarizer.extract_badges(content_text, references)
            
            # Create snippet
            snippet = content_text[:300] + "..." if len(content_text) > 300 else content_text
            
            # Create Card object
            card = Card(
                content_id=content_id,
                type=content_type,
                title=raw_article['title'],
                source=raw_article['source'],
                published_at=raw_article['published_at'],
                tl_dr=tl_dr,
                summary=summary,
                why_it_matters=why_it_matters,
                badges=badges,
                tags=tags,
                references=references,
                snippet=snippet,
                synthesis_failed=False
            )
            
            return card
            
        except Exception as e:
            print(f"Error processing article: {e}")
            return None
    
    def ingest_pipeline(self) -> Dict[str, Any]:
        """Run the complete ingestion pipeline"""
        try:
            print("Starting ingestion pipeline...")
            
            # Fetch RSS feeds
            raw_articles = self.fetch_rss_feeds()
            print(f"Fetched {len(raw_articles)} raw articles")
            
            if not raw_articles:
                return {
                    'success': False,
                    'message': 'No articles fetched',
                    'new_articles': 0,
                    'total_articles': 0
                }
            
            # Process articles
            processed_cards = []
            embeddings = []
            
            for raw_article in raw_articles:
                try:
                    # Process article
                    card = self.process_article(raw_article)
                    if not card:
                        continue
                    
                    # Check if article already exists
                    existing = db_manager.get_article_by_id(card.content_id)
                    if existing:
                        print(f"Article {card.content_id} already exists, skipping")
                        continue
                    
                    # Generate embedding
                    try:
                        embedding = summarizer.embed_text(f"{card.title} {card.summary}")
                        embeddings.append(embedding)
                        processed_cards.append(card)
                    except Exception as e:
                        print(f"Error generating embedding for {card.content_id}: {e}")
                        continue
                    
                except Exception as e:
                    print(f"Error processing article: {e}")
                    continue
            
            if not processed_cards:
                return {
                    'success': False,
                    'message': 'No new articles to process',
                    'new_articles': 0,
                    'total_articles': db_manager.get_article_count()
                }
            
            # Store in database
            db_success_count = 0
            for card in processed_cards:
                if db_manager.insert_article(card):
                    db_success_count += 1
            
            # Store in vector store
            vector_success = False
            if processed_cards and embeddings:
                try:
                    vector_success = vector_store.upsert_documents(processed_cards, embeddings)
                except Exception as e:
                    print(f"Error storing in vector store: {e}")
            
            # Return results
            result = {
                'success': True,
                'message': f'Processed {db_success_count} new articles',
                'new_articles': db_success_count,
                'total_articles': db_manager.get_article_count(),
                'vector_store_success': vector_success
            }
            
            print(f"Ingestion completed: {result}")
            return result
            
        except Exception as e:
            print(f"Error in ingestion pipeline: {e}")
            return {
                'success': False,
                'message': f'Ingestion failed: {str(e)}',
                'new_articles': 0,
                'total_articles': db_manager.get_article_count()
            }
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get ingestion statistics"""
        try:
            total_articles = db_manager.get_article_count()
            
            # Get recent articles count
            recent_articles = db_manager.get_recent_articles(limit=1000, days=7)
            recent_count = len(recent_articles)
            
            return {
                'total_articles': total_articles,
                'recent_articles_7d': recent_count,
                'rss_sources': len(self.rss_sources),
                'last_ingestion': datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Error getting ingestion stats: {e}")
            return {
                'total_articles': 0,
                'recent_articles_7d': 0,
                'rss_sources': 0,
                'last_ingestion': None
            }

# Global ingestion pipeline
ingestion_pipeline = RSSIngestionPipeline()
```

## Key Features to Implement

### 1. RSS Feed Fetching
- **Multiple Sources**: Support for HuggingFace, OpenAI, and Hacker News feeds
- **Error Handling**: Graceful handling of feed parsing errors
- **Content Extraction**: Extract full content from RSS entries
- **Date Parsing**: Handle various date formats from different sources

### 2. Content Processing
- **AI Summarization**: Process content through Azure OpenAI
- **Metadata Extraction**: Generate tags, badges, and references
- **Content Cleaning**: Remove HTML tags and normalize text
- **Type Detection**: Automatically classify content type

### 3. Storage Integration
- **Database Storage**: Store processed articles in SQLite
- **Vector Storage**: Store embeddings in Azure AI Search
- **Deduplication**: Prevent duplicate articles
- **Error Recovery**: Handle partial failures gracefully

### 4. Pipeline Orchestration
- **Batch Processing**: Process multiple articles efficiently
- **Progress Tracking**: Log progress and statistics
- **Error Reporting**: Detailed error reporting and recovery
- **Performance Monitoring**: Track processing times and success rates

## RSS Sources Configuration

### Supported Sources
1. **HuggingFace Blog**: https://huggingface.co/blog/feed.xml
2. **OpenAI News**: https://openai.com/news/rss.xml
3. **Hacker News AI**: https://hnrss.org/newest?q=AI

### Content Extraction Strategy
- **Primary Content**: Use `content` field if available
- **Fallback Content**: Use `summary` or `description` fields
- **HTML Cleaning**: Remove HTML tags and normalize whitespace
- **Length Validation**: Ensure content is substantial enough for processing

## Processing Pipeline Flow

### 1. Fetch Phase
```
RSS Sources → Feed Parser → Raw Articles
```

### 2. Processing Phase
```
Raw Articles → Content Extraction → AI Summarization → Metadata Generation
```

### 3. Storage Phase
```
Processed Cards → Database Storage → Vector Storage → Completion
```

## Error Handling Strategy

### 1. Feed-Level Errors
- **Network Issues**: Retry with exponential backoff
- **Parsing Errors**: Log warnings but continue processing
- **Invalid Feeds**: Skip problematic feeds, continue with others

### 2. Article-Level Errors
- **Processing Failures**: Skip individual articles, continue batch
- **AI Failures**: Use fallback summarization
- **Storage Failures**: Log errors, continue with remaining articles

### 3. Recovery Mechanisms
- **Partial Success**: Report successful articles even if some fail
- **Retry Logic**: Retry failed operations with backoff
- **Fallback Content**: Use basic extraction when AI fails

## Validation Checklist
- [ ] RSS feeds are fetched successfully from all sources
- [ ] Content extraction works for different feed formats
- [ ] AI summarization produces valid output
- [ ] Database storage works correctly
- [ ] Vector storage integration functions properly
- [ ] Deduplication prevents duplicate articles
- [ ] Error handling works for various failure scenarios
- [ ] Statistics and monitoring provide useful insights
- [ ] Pipeline can handle large batches of articles
- [ ] Recovery mechanisms work for partial failures

## Next Steps
After completing this todo, proceed to "06-scheduler-setup" to implement the daily job scheduler for automatic morning brief generation.
