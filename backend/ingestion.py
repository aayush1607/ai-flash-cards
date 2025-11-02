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
            content_id = generate_content_id(title, source_name, published_at)
            
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
    
    def ingest_pipeline(self, limit_per_feed: int = 10, batch_size: int = None, clear_db: bool = False) -> Dict[str, Any]:
        """Run the complete ingestion pipeline with batch filtering
        
        Two-phase process:
        1. Extract and save raw articles to SQLite
        2. Summarize unsummarized articles from SQLite
        """
        try:
            print("Starting ingestion pipeline...")
            
            # ============================================================
            # PHASE 1: Extract and save raw articles
            # ============================================================
            print("Phase 1: Fetching articles from RSS feeds...")
            
            # Fetch RSS feeds with limit per feed (BEFORE clearing database)
            raw_articles = self.fetch_rss_feeds(limit_per_feed)
            print(f"Fetched {len(raw_articles)} raw articles")
            
            if not raw_articles:
                print("⚠️  No articles fetched - skipping database clear and keeping existing data")
                return {
                    'success': False,
                    'message': 'No articles fetched - database not cleared',
                    'new_articles': 0,
                    'total_articles': db_manager.get_article_count()
                }
            
            # Only clear database if we successfully fetched articles and clear_db is requested
            if clear_db:
                print("Clearing existing articles from database (articles fetched successfully)...")
                cleared_count = db_manager.clear_all_articles()
                print(f"Cleared {cleared_count} existing articles")
            
            # Save ALL raw articles to database (no relevance check or summarization here)
            print("Saving all raw articles to database...")
            raw_saved_count = 0
            for raw_article in raw_articles:
                try:
                    if db_manager.insert_raw_article(raw_article):
                        raw_saved_count += 1
                except Exception as e:
                    print(f"Error saving raw article {raw_article.get('content_id', 'unknown')}: {e}")
                    continue
            
            print(f"Saved {raw_saved_count} raw articles to database")
            
            # Return results - relevance check and summarization will be done by separate scheduled jobs
            result = {
                'success': True,
                'message': f'Saved {raw_saved_count} raw articles (relevance check and summarization will be done by scheduled jobs)',
                'new_articles': raw_saved_count,
                'raw_articles_saved': raw_saved_count,
                'total_articles': db_manager.get_article_count()
            }
            
            print(f"Ingestion completed: {result}")
            return result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in ingestion pipeline: {e}")
            print(f"Full traceback:\n{error_trace}")
            # Also log if logger is available
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in ingestion pipeline: {e}", exc_info=True)
            except:
                pass
            return {
                'success': False,
                'message': f'Ingestion failed: {str(e)}',
                'error': str(e),
                'traceback': error_trace,
                'new_articles': 0,
                'total_articles': db_manager.get_article_count()
            }
    
    def run_relevance_check_job(self, batch_size: int = 10) -> Dict[str, Any]:
        """Run relevance check on unchecked articles (called by scheduler).
        Prioritizes most recently published articles."""
        try:
            print("Starting relevance check job...")
            
            # Get articles that haven't been checked for relevance (prioritize most recent)
            # Use batch_size * 2 to get a larger pool for batch filtering, but prioritize recent ones
            unchecked_articles = db_manager.get_unchecked_relevance_articles(limit=batch_size * 10)
            print(f"Found {len(unchecked_articles)} unchecked articles (processing most recent first)")
            
            if not unchecked_articles:
                return {
                    'success': True,
                    'message': 'No articles to check for relevance',
                    'checked': 0,
                    'relevant': 0
                }
            
            # Convert to dict format for batch filtering
            raw_articles = []
            for article in unchecked_articles:
                raw_articles.append({
                    'content_id': article.content_id,
                    'title': article.raw_title,
                    'content': article.raw_content or article.raw_description or '',
                    'source': article.source
                })
            
            # Batch filter for relevance (returns dict: content_id -> score)
            relevant_scores = self._batch_filter_relevant_articles(raw_articles, batch_size)
            print(f"Found {len(relevant_scores)} relevant articles out of {len(unchecked_articles)}")
            
            # Update articles with relevance results and scores
            checked_count = 0
            relevant_count = 0
            
            for article in unchecked_articles:
                try:
                    content_id = article.content_id
                    is_relevant = content_id in relevant_scores
                    score = relevant_scores.get(content_id)  # Get score if relevant, None otherwise
                    increment_failure = False
                    
                    if db_manager.update_relevance_check(content_id, is_relevant, relevance_score=score, increment_failure=increment_failure):
                        checked_count += 1
                        if is_relevant:
                            relevant_count += 1
                except Exception as e:
                    print(f"Error updating relevance for {article.content_id}: {e}")
                    # Increment failure count on error
                    db_manager.update_relevance_check(article.content_id, False, relevance_score=None, increment_failure=True)
                    continue
            
            result = {
                'success': True,
                'message': f'Checked {checked_count} articles, {relevant_count} relevant',
                'checked': checked_count,
                'relevant': relevant_count
            }
            
            print(f"Relevance check completed: {result}")
            return result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in relevance check job: {e}")
            print(f"Full traceback:\n{error_trace}")
            # Also log if logger is available
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in relevance check job: {e}", exc_info=True)
            except:
                pass
            return {
                'success': False,
                'message': f'Relevance check failed: {str(e)}',
                'error': str(e),
                'traceback': error_trace,
                'checked': 0,
                'relevant': 0
            }
    
    def run_summarization_job(self, limit: int = 20) -> Dict[str, Any]:
        """Run summarization on relevant but unsummarized articles (called by scheduler)"""
        try:
            print("Starting summarization job...")
            
            # Get articles that are relevant but not summarized yet
            unsummarized = db_manager.get_unsummarized_articles(limit=limit)
            print(f"Found {len(unsummarized)} articles ready for summarization")
            
            if not unsummarized:
                return {
                    'success': True,
                    'message': 'No articles to summarize',
                    'summarized': 0
                }
            
            # Process articles for summarization
            processed_cards = []
            embeddings = []
            summarized_count = 0
            failed_count = 0
            
            for article in unsummarized:
                try:
                    # Convert Article to raw_article dict format for processing
                    raw_article = {
                        'content_id': article.content_id,
                        'title': article.raw_title,
                        'link': article.raw_link,
                        'description': article.raw_description or '',
                        'content': article.raw_content or '',
                        'source': article.source,
                        'published_at': article.published_at
                    }
                    
                    # Process article (summarize)
                    card = self.process_article(raw_article)
                    if not card:
                        print(f"Failed to process article {article.content_id}")
                        db_manager.increment_summarization_failure(article.content_id)
                        failed_count += 1
                        continue
                    
                    # Update article with summary
                    if db_manager.update_article_summary(article.content_id, card):
                        summarized_count += 1
                        
                        # Generate embedding for vector store
                        try:
                            embedding = summarizer.embed_text(f"{card.title} {card.tl_dr} {card.summary} {card.why_it_matters}")
                            embeddings.append(embedding)
                            processed_cards.append(card)
                        except Exception as e:
                            print(f"Error generating embedding for {card.content_id}: {e}")
                            # Don't fail the article if embedding fails
                            continue
                    else:
                        db_manager.increment_summarization_failure(article.content_id)
                        failed_count += 1
                    
                except Exception as e:
                    print(f"Error processing article {article.content_id}: {e}")
                    db_manager.increment_summarization_failure(article.content_id)
                    failed_count += 1
                    continue
            
            # Store in vector store
            vector_success = False
            if processed_cards and embeddings:
                try:
                    vector_success = vector_store.upsert_documents(processed_cards, embeddings)
                except Exception as e:
                    print(f"Error storing in vector store: {e}")
            
            # After processing, optionally clean up stale documents from vector store
            # Get all processed articles from database to compare with vector store
            try:
                from backend.models import Article
                with db_manager.get_session() as session:
                    # Get all processed articles (that should be in vector store)
                    # Articles that are summarized should be in vector store
                    processed_articles = session.query(Article).filter(
                        Article.is_summarized == True
                    ).all()
                    valid_content_ids = [article.content_id for article in processed_articles]
                
                if valid_content_ids:
                    print(f"Cleaning up stale documents from vector store (keeping {len(valid_content_ids)} valid)...")
                    stale_count = vector_store.cleanup_stale_documents(valid_content_ids)
                    if stale_count > 0:
                        print(f"Removed {stale_count} stale documents from vector store")
            except Exception as cleanup_error:
                print(f"Warning: Could not cleanup stale documents: {cleanup_error}")
                # Don't fail the job if cleanup fails
            
            result = {
                'success': True,
                'message': f'Summarized {summarized_count} articles, {failed_count} failed',
                'summarized': summarized_count,
                'failed': failed_count,
                'vector_store_success': vector_success
            }
            
            print(f"Summarization completed: {result}")
            return result
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Error in summarization job: {e}")
            print(f"Full traceback:\n{error_trace}")
            # Also log if logger is available
            try:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error in summarization job: {e}", exc_info=True)
            except:
                pass
            return {
                'success': False,
                'message': f'Summarization failed: {str(e)}',
                'error': str(e),
                'traceback': error_trace,
                'summarized': 0,
                'failed': 0
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

    def _batch_filter_relevant_articles(self, articles: List[Dict[str, Any]], batch_size: int = 10) -> Dict[str, float]:
        """Use AI to filter relevant articles in batches, returning dict mapping content_id -> relevance_score"""
        try:
            relevant_scores = {}  # Map content_id -> score
            
            # Process articles in batches
            for i in range(0, len(articles), batch_size):
                batch = articles[i:i + batch_size]
                
                # Create batch prompt with article summaries
                batch_prompt = self._create_batch_filter_prompt(batch)
                
                # Get AI response for batch
                response = summarizer.client.chat.completions.create(
                    model=summarizer.deployment_name,
                    messages=[{"role": "user", "content": batch_prompt}],
                    max_tokens=1000,  # Increased for detailed score responses with reasons
                    temperature=0.1
                )
                
                # Parse response to get content_ids with scores
                batch_scores = self._parse_batch_filter_response(response.choices[0].message.content, batch)
                relevant_scores.update(batch_scores)
                
                print(f"Batch {i//batch_size + 1}: {len(batch_scores)}/{len(batch)} articles relevant")
            
            print(f"Total relevant articles: {len(relevant_scores)}/{len(articles)}")
            return relevant_scores
            
        except Exception as e:
            print(f"Error in batch filtering: {e}")
            # If batch filtering fails, return empty dict (fail-safe)
            return {}

    def _create_batch_filter_prompt(self, batch: List[Dict[str, Any]]) -> str:
        """Create a prompt for batch filtering articles with quality scoring"""
        articles_text = ""
        for i, article in enumerate(batch, 1):
            title = article.get('title', 'No Title')
            content_preview = article.get('content', '')[:500]  # Increased to 500 chars for better evaluation
            source = article.get('source', 'Unknown')
            
            articles_text += f"""
Article {i}:
- Title: {title}
- Source: {source}
- Content Preview: {content_preview}...
---
"""
        
        prompt = f"""
You are a quality filter for an AI research aggregator. Your task is to evaluate articles and assign a relevance score (0.0-1.0) based on value and quality.

## Scoring Guidelines:

**Score 0.9-1.0 (High-Value)** - Include only if:
- Research papers with novel contributions
- Official announcements from major tech companies (OpenAI, Google, Microsoft, etc.)
- Significant technical breakthroughs with detailed explanations
- In-depth technical analysis with substantial content (500+ words)
- Formal publications from reputable sources

**Score 0.7-0.9 (Medium-Value)** - Include if:
- Quality blog posts with technical depth
- Well-researched articles explaining AI concepts
- Industry news with technical details
- Tutorials or guides with substantive content
- Announcements with technical specifications

**Score < 0.7 (Low-Value)** - EXCLUDE these:
- Short comments or opinions (< 200 words, casual tone)
- Social media posts or tweet-like content
- Casual mentions of AI without substance
- Question posts ("Anyone tried X?")
- Simple links without context
- Reddit/Hacker News comment threads
- Non-technical discussions
- Speculation without evidence

## Few-Shot Examples:

Example 1:

User: You are a quality filter for an AI research aggregator. Your task is to evaluate articles and assign a relevance score (0.0-1.0) based on value and quality.

Article 1:
Title: "GPT-4 Technical Report"
Source: OpenAI
Content Preview: "We report the development of GPT-4, a large-scale, multimodal model which can accept both image and text inputs and produce text outputs. While less capable than humans in many real-world scenarios, GPT-4 exhibits human-level performance on various professional and academic benchmarks. This report provides technical details about GPT-4's architecture, training methodology, and evaluation results across multiple domains..."
**Why High Score**: Official research report, technical depth, substantial content, from authoritative source.

Article 2:
Title: "What do you think about ChatGPT?"
Source: Hacker News
Content Preview: "I've been using ChatGPT for a few weeks and it's pretty cool. Anyone else tried it? What do you think about the responses? I'm wondering if it will replace Google search someday..."
**Why Low Score**: Casual comment, opinion-based, lacks technical substance, question format, social discussion.

Your response:
{{
    "scores": [
        {{"article_number": 1, "score": 0.95, "reason": "Official research report, technical depth, substantial content, from authoritative source."}},
        {{"article_number": 2, "score": 0.3, "reason": "Casual comment, opinion-based, lacks technical substance, question format, social discussion."}},
    ]
}}

Example 2:

User: You are a quality filter for an AI research aggregator. Your task is to evaluate articles and assign a relevance score (0.0-1.0) based on value and quality.

Article 1:
Title: "Understanding Transformer Architecture: A Deep Dive"
Source: Towards Data Science
Content Preview: "In this article, we'll explore the transformer architecture that powers modern LLMs. We'll break down the attention mechanism, explain how self-attention works, and discuss the encoder-decoder structure. This guide includes code examples and visualizations to help you understand these concepts..."
**Why Medium Score**: Educational content with technical depth, but not original research.

Article 2:
Title: "Stock Market Update: Tech Stocks Rally"
Source: Financial News
Content Preview: "Technology stocks saw significant gains today as investors responded positively to earnings reports. Major tech companies including Apple, Microsoft, and Google saw their shares rise..."
**Why Low Score**: Not about AI/ML research, general financial news.

Article 3:
Title: "Check out this AI tool"
Source: Hacker News
Content Preview: "Found this cool AI tool: https://example.com/tool. Seems useful for image generation. Worth checking out!"
**Why Low Score**: Very short, just a link with minimal context, no technical information, casual mention.

Article 4:
Title: "Efficient Fine-Tuning Strategies for Large Language Models"
Source: AI Research Blog
Content Preview: "Fine-tuning large language models can be computationally expensive. In this article, we explore several efficient fine-tuning techniques including LoRA (Low-Rank Adaptation), QLoRA, and adapter layers. We compare their performance, memory requirements, and implementation complexity. Practical examples and benchmarks are provided..."
**Why Medium Score**: Technical depth, substantive content, educational value, but not original research paper.

Your response:
{{
    "scores": [
        {{"article_number": 1, "score": 0.85, "reason": "Educational content with technical depth, but not original research paper."}},
        {{"article_number": 2, "score": 0.3, "reason": "Not about AI/ML research, general financial news."}},
        {{"article_number": 3, "score": 0.1, "reason": "Very short, just a link with minimal context, no technical information, casual mention."}},
        {{"article_number": 4, "score": 0.85, "reason": "Technical depth, substantive content, educational value, but not original research paper."}},
    ]
}}

## Your Task:

You are a quality filter for an AI research aggregator. Your task is to evaluate articles and assign a relevance score (0.0-1.0) based on value and quality.

{articles_text}

Return your evaluation in this exact JSON format:
{{
    "scores": [
        {{"article_number": 1, "score": float, "reason": "Brief explanation"}},
        {{"article_number": 2, "score": float, "reason": "Brief explanation"}},
        ...
    ]
}}

For each article, provide:
- article_number: The article number (1, 2, 3, etc.)
- score: A float between 0.0 and 1.0
- reason: A brief 1-sentence explanation for the score

Be strict with low-quality content. 
Return ONLY the JSON response, no other text.
"""
        return prompt

    def _parse_batch_filter_response(self, response: str, batch: List[Dict[str, Any]], threshold: float = 0.7) -> Dict[str, float]:
        """Parse AI response to extract content IDs with scores above threshold, returns dict mapping content_id -> score"""
        try:
            print(f"AI Response: {response[:300]}...")  # Debug output
            
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                scores_list = result.get('scores', [])
                
                if not scores_list:
                    print("No scores found in response")
                    return {}
                
                print(f"Parsed {len(scores_list)} article scores")
                
                # Map scores to content IDs (only include articles with score >= threshold)
                relevant_scores = {}  # content_id -> score
                for score_entry in scores_list:
                    article_number = score_entry.get('article_number')
                    score = float(score_entry.get('score', 0.0))
                    reason = score_entry.get('reason', 'No reason provided')
                    
                    if article_number is None:
                        continue
                    
                    try:
                        # Convert 1-based article number to 0-based index
                        index = int(article_number) - 1
                        if 0 <= index < len(batch):
                            content_id = batch[index]['content_id']
                            
                            # Only include if score >= threshold
                            if score >= threshold:
                                relevant_scores[content_id] = score
                                print(f"Article {article_number}: Score {score:.2f} - {reason}")
                            else:
                                print(f"Article {article_number}: Score {score:.2f} below threshold {threshold} - {reason}")
                        else:
                            print(f"Invalid article number: {article_number} (batch size: {len(batch)})")
                    except (ValueError, TypeError) as e:
                        print(f"Error processing article number {article_number}: {e}")
                        continue
                
                print(f"Filtered to {len(relevant_scores)}/{len(batch)} articles above threshold {threshold}")
                return relevant_scores
            else:
                # Fallback: return empty dict if JSON parsing fails (strict mode)
                print("Failed to parse JSON, returning empty dict (strict filtering)")
                return {}
                
        except Exception as e:
            print(f"Error parsing batch filter response: {e}")
            print(f"Response was: {response}")
            # Fallback: return empty dict if parsing fails (strict mode)
            return {}

# Global ingestion pipeline
ingestion_pipeline = RSSIngestionPipeline()
