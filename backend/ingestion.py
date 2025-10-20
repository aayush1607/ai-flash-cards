import feedparser
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import re
import json
from backend.models import Card, Reference, generate_content_id, detect_content_type
from backend.database import db_manager
from backend.vector_store import vector_store
from backend.summarizer import summarizer

class RSSIngestionPipeline:
    """RSS ingestion and processing pipeline"""
    
    def __init__(self):
        self.rss_sources = [
            "https://huggingface.co/blog/feed.xml",
            "https://openai.com/news/rss.xml", 
            "https://hnrss.org/newest?q=AI",
            "https://deepmind.google/blog/rss.xml",
            "https://news.microsoft.com/feed/",
            "https://developer.nvidia.com/blog/feed",
            "https://aws.amazon.com/blogs/machine-learning/feed/",
            "https://export.arxiv.org/rss/cs.LG",
            "https://news.mit.edu/rss/topic/artificial-intelligence2"
        ]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'AIFlash/1.0 (AI Research Aggregator)'
        })
    
    def fetch_rss_feeds(self, limit_per_feed: int = None) -> List[Dict[str, Any]]:
        """Fetch and parse all RSS feeds"""
        all_articles = []
        
        for source_url in self.rss_sources:
            try:
                print(f"Fetching RSS feed: {source_url}")
                articles = self._fetch_single_feed(source_url, limit_per_feed)
                all_articles.extend(articles)
                print(f"Fetched {len(articles)} articles from {source_url}")
            except Exception as e:
                print(f"Error fetching {source_url}: {e}")
                continue
        
        return all_articles
    
    def _fetch_single_feed(self, feed_url: str, limit: int = None) -> List[Dict[str, Any]]:
        """Fetch and parse a single RSS feed"""
        try:
            # Parse RSS feed
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                print(f"Warning: RSS feed {feed_url} has parsing issues")
            
            articles = []
            for i, entry in enumerate(feed.entries):
                # Apply limit if specified
                if limit and i >= limit:
                    break
                    
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
            
            # Generate content ID
            content_id = generate_content_id(title, link, source_name)
            
            # Create article dictionary
            article = {
                'content_id': content_id,
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
        elif 'deepmind.google' in feed_url:
            return 'DeepMind'
        elif 'microsoft.com' in feed_url:
            return 'Microsoft'
        elif 'nvidia.com' in feed_url:
            return 'NVIDIA'
        elif 'aws.amazon.com' in feed_url:
            return 'AWS'
        elif 'arxiv.org' in feed_url:
            return 'arXiv'
        elif 'mit.edu' in feed_url:
            return 'MIT'
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
    
    async def ingest_pipeline(self, limit_per_feed: int = 10, batch_size: int = 10, clear_db: bool = False) -> Dict[str, Any]:
        """Run the complete ingestion pipeline with batch filtering"""
        try:
            print("Starting ingestion pipeline...")
            
            # Clear database if requested
            if clear_db:
                print("Clearing existing articles from database...")
                cleared_count = db_manager.clear_all_articles()
                print(f"Cleared {cleared_count} existing articles")
            
            # Fetch RSS feeds with limit per feed
            raw_articles = self.fetch_rss_feeds(limit_per_feed)
            print(f"Fetched {len(raw_articles)} raw articles")
            
            if not raw_articles:
                return {
                    'success': False,
                    'message': 'No articles fetched',
                    'new_articles': 0,
                    'total_articles': 0
                }
            
            # Batch filter for relevance
            print("Filtering articles for relevance...")
            relevant_ids = await self._batch_filter_relevant_articles(raw_articles, batch_size)
            print(f"Found {len(relevant_ids)} relevant articles out of {len(raw_articles)}")
            
            # Filter articles to only process relevant ones
            relevant_articles = [article for article in raw_articles if article['content_id'] in relevant_ids]
            
            # Process relevant articles
            processed_cards = []
            embeddings = []
            
            for raw_article in relevant_articles:
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

    async def _batch_filter_relevant_articles(self, articles: List[Dict[str, Any]], batch_size: int = 10) -> List[str]:
        """Use AI to filter relevant articles in batches, returning content_ids of relevant articles"""
        try:
            relevant_ids = []
            
            # Process articles in batches
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                
                # Create batch prompt with article summaries
                batch_prompt = self._create_batch_filter_prompt(batch)
                
                # Get AI response for batch
                response = summarizer.client.chat.completions.create(
                    model=summarizer.deployment_name,
                    messages=[{"role": "user", "content": batch_prompt}],
                    max_tokens=500,
                    temperature=0.1
                )
                
                # Parse response to get relevant content_ids
                batch_relevant_ids = self._parse_batch_filter_response(response.choices[0].message.content, batch)
                relevant_ids.extend(batch_relevant_ids)
                
                print(f"Batch {i//batch_size + 1}: {len(batch_relevant_ids)}/{len(batch)} articles relevant")
            
            print(f"Total relevant articles: {len(relevant_ids)}/{len(articles)}")
            return relevant_ids
            
        except Exception as e:
            print(f"Error in batch filtering: {e}")
            # If batch filtering fails, return all article IDs (fail-safe)
            return [article['content_id'] for article in articles]

    def _create_batch_filter_prompt(self, batch: List[Dict[str, Any]]) -> str:
        """Create a prompt for batch filtering articles"""
        articles_text = ""
        for i, article in enumerate(batch, 1):
            title = article.get('title', 'No Title')
            content_preview = article.get('content', '')[:200]  # First 200 chars of content
            source = article.get('source', 'Unknown')
            
            articles_text += f"""
Article {i}:
- Title: {title}
- Source: {source}
- Preview: {content_preview}...
---
"""
        
        prompt = f"""
You are filtering articles for an AI research aggregator. From the following articles, identify which ones are relevant to AI, machine learning, or technology research.

{articles_text}

Return ONLY the article numbers of relevant articles in this exact JSON format:
{{"relevant_ids": ["article_1", "article_2", "article_3", ...]}}

Only include articles that are:
1. About AI, ML, or technology research
2. Recent developments in tech
3. Academic papers or research
4. Industry news about AI/tech companies

Exclude articles about:
- General business news unrelated to tech
- Politics unrelated to AI/tech
- Sports, entertainment, or lifestyle
- Non-technical content

Return the JSON response only.
"""
        return prompt

    def _parse_batch_filter_response(self, response: str, batch: List[Dict[str, Any]]) -> List[str]:
        """Parse AI response to extract relevant content IDs"""
        try:
            print(f"AI Response: {response[:200]}...")  # Debug output
            
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                article_numbers = result.get('relevant_ids', [])
                print(f"Parsed article numbers: {article_numbers}")
                
                # Map article numbers back to content IDs
                relevant_content_ids = []
                for article_num in article_numbers:
                    # Extract number from "article_X" format
                    if article_num.startswith('article_'):
                        try:
                            index = int(article_num.split('_')[1]) - 1  # Convert to 0-based index
                            if 0 <= index < len(batch):
                                relevant_content_ids.append(batch[index]['content_id'])
                        except (ValueError, IndexError):
                            print(f"Invalid article number: {article_num}")
                            continue
                
                print(f"Mapped to content IDs: {relevant_content_ids}")
                return relevant_content_ids
            else:
                # Fallback: return all IDs if JSON parsing fails
                print("Failed to parse JSON, returning all articles")
                return [article['content_id'] for article in batch]
                
        except Exception as e:
            print(f"Error parsing batch filter response: {e}")
            print(f"Response was: {response}")
            # Fallback: return all IDs if parsing fails
            return [article['content_id'] for article in batch]

# Global ingestion pipeline
ingestion_pipeline = RSSIngestionPipeline()
