import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, text, func
from backend.config import config
from backend.models import Article, Card, Reference, create_database_engine, create_tables, get_session_factory

class DatabaseManager:
    """Database manager for CRUD operations"""
    
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(config.database_path), exist_ok=True)
        
        # Create engine and tables
        self.engine = create_database_engine(config.database_path)
        create_tables(self.engine)
        
        # Initialize SessionLocal first (before migration) so it's always available
        self.SessionLocal = get_session_factory(self.engine)
        
        # Run migrations to add new columns if needed (after SessionLocal is set)
        try:
            self._migrate_schema()
        except Exception as e:
            print(f"Warning: Migration failed but continuing: {e}")
            # Don't raise - let the system continue even if migration fails
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
    def _migrate_schema(self):
        """Migrate database schema to add new columns if they don't exist"""
        print("Running database schema migration...")
        try:
            # Check if articles table exists using a simple query
            with self.get_session() as session:
                try:
                    session.execute(text("SELECT 1 FROM articles LIMIT 1"))
                    print("Articles table exists, checking for missing columns...")
                except Exception:
                    print("Articles table doesn't exist yet, skipping migration")
                    return
            
            # Get existing columns using PRAGMA table_info
            with self.get_session() as session:
                result = session.execute(text("PRAGMA table_info(articles)"))
                existing_columns = [row[1] for row in result.fetchall()]  # Column name is at index 1
                print(f"Existing columns: {existing_columns}")
                
                # Columns to add if missing
                new_columns = {
                    'raw_title': ("VARCHAR(500)", "ALTER TABLE articles ADD COLUMN raw_title VARCHAR(500)"),
                    'raw_description': ("TEXT", "ALTER TABLE articles ADD COLUMN raw_description TEXT"),
                    'raw_content': ("TEXT", "ALTER TABLE articles ADD COLUMN raw_content TEXT"),
                    'raw_link': ("VARCHAR(500)", "ALTER TABLE articles ADD COLUMN raw_link VARCHAR(500)"),
                    'is_relevance_check_done': ("BOOLEAN DEFAULT 0", "ALTER TABLE articles ADD COLUMN is_relevance_check_done BOOLEAN DEFAULT 0"),
                    'is_summarized': ("BOOLEAN DEFAULT 0", "ALTER TABLE articles ADD COLUMN is_summarized BOOLEAN DEFAULT 0"),
                    'failure_count': ("INTEGER DEFAULT 0", "ALTER TABLE articles ADD COLUMN failure_count INTEGER DEFAULT 0"),
                    'is_relevant': ("BOOLEAN", "ALTER TABLE articles ADD COLUMN is_relevant BOOLEAN"),
                    'relevance_score': ("REAL", "ALTER TABLE articles ADD COLUMN relevance_score REAL"),
                    'summarized_at': ("DATETIME", "ALTER TABLE articles ADD COLUMN summarized_at DATETIME")
                }
                
                # Check if we need to modify existing 'type' column to be nullable
                # SQLite doesn't support MODIFY COLUMN directly, but we can handle this by ensuring
                # we always provide a default value when type is NULL
                if 'type' in existing_columns:
                    print("Type column exists - note: SQLite doesn't allow changing NOT NULL constraints, but we'll handle NULLs in code")
                
                # Check and add missing columns
                columns_added = []
                for column_name, (_column_type, alter_sql) in new_columns.items():
                    if column_name not in existing_columns:
                        try:
                            print(f"Adding missing column: {column_name}")
                            session.execute(text(alter_sql))
                            session.commit()
                            columns_added.append(column_name)
                            print(f"✓ Successfully added column {column_name}")
                        except Exception as e:
                            session.rollback()
                            print(f"✗ Error adding column {column_name}: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"Column {column_name} already exists, skipping")
                
                if columns_added:
                    print(f"Migration complete: Added {len(columns_added)} columns: {columns_added}")
                else:
                    print("Migration complete: No new columns needed")
                
                # Handle migration of existing data
                # Check if we have old columns (title, summary) and need to populate raw fields
                if 'title' in existing_columns or 'raw_title' in existing_columns:
                    try:
                        # Check if there are any articles to migrate
                        result = session.execute(text("SELECT COUNT(*) FROM articles")).scalar()
                        if result > 0:
                            print(f"Found {result} existing articles, migrating data...")
                            
                            # Build update query dynamically based on what columns exist
                            update_parts = []
                            
                            if 'title' in existing_columns and 'raw_title' in existing_columns:
                                update_parts.append("raw_title = COALESCE(NULLIF(raw_title, ''), title, '')")
                            
                            if 'summary' in existing_columns:
                                if 'raw_description' in existing_columns:
                                    update_parts.append("raw_description = COALESCE(NULLIF(raw_description, ''), summary, '')")
                                if 'raw_content' in existing_columns:
                                    update_parts.append("raw_content = COALESCE(NULLIF(raw_content, ''), summary, '')")
                            
                            if 'raw_link' in existing_columns:
                                update_parts.append("raw_link = COALESCE(NULLIF(raw_link, ''), '')")
                            
                            if 'summary' in existing_columns and 'is_summarized' in existing_columns:
                                update_parts.append("""
                                    is_summarized = CASE 
                                        WHEN summary IS NOT NULL AND summary != '' THEN 1 
                                        ELSE 0 
                                    END
                                """)
                            
                            if update_parts:
                                update_sql = f"""
                                    UPDATE articles 
                                    SET {', '.join(update_parts)}
                                    WHERE (raw_title IS NULL OR raw_title = '') 
                                       OR (raw_link IS NULL OR raw_link = '')
                                       OR is_summarized IS NULL
                                """
                                session.execute(text(update_sql))
                                session.commit()
                                print(f"✓ Migrated data for {result} existing articles")
                    except Exception as e:
                        session.rollback()
                        print(f"⚠ Warning: Could not migrate existing data: {e}")
                        import traceback
                        traceback.print_exc()
                
        except Exception as e:
            print(f"✗ Error during schema migration: {e}")
            import traceback
            traceback.print_exc()
    
    def insert_article(self, card: Card) -> bool:
        """Insert new article"""
        try:
            with self.get_session() as session:
                # Check if article already exists
                existing = session.query(Article).filter(
                    Article.content_id == card.content_id
                ).first()
                
                if existing:
                    return False  # Already exists
                
                # Create new article
                article = Article.from_card(card)
                session.add(article)
                session.commit()
                return True
        except Exception as e:
            print(f"Error inserting article: {e}")
            return False
    
    def get_article_by_id(self, content_id: str) -> Optional[Card]:
        """Get article by content ID (with smart fallback logic)"""
        try:
            with self.get_session() as session:
                article = session.query(Article).filter(
                    Article.content_id == content_id
                ).first()
                
                if not article:
                    return None
                
                # Try fully processed first
                if article.is_relevance_check_done and article.is_summarized and article.is_relevant:
                    return article.to_card()
                
                # Fallback 1: Relevance-checked and marked relevant (preferred over just summarized)
                if article.is_relevance_check_done and article.is_relevant:
                    if article.is_summarized:
                        return article.to_card()
                    else:
                        # Create basic card from raw data
                        return Card(
                            content_id=article.content_id,
                            type=article.type or 'blog',
                            title=article.raw_title,
                            source=article.source,
                            published_at=article.published_at,
                            tl_dr=article.raw_title[:140],
                            summary=article.raw_description or article.raw_content or '',
                            why_it_matters='Content is being processed.',
                            badges=[],
                            tags=[],
                            references=[Reference(label="Source", url=article.raw_link)],
                            snippet=article.raw_description or '',
                            synthesis_failed=False
                        )
                
                # Fallback 2: Raw article - create basic card
                # Note: Summarized articles are not possible here because summarization only happens
                # for relevance-checked and relevant articles, which would have been caught above
                return Card(
                    content_id=article.content_id,
                    type=article.type or 'blog',
                    title=article.raw_title,
                    source=article.source,
                    published_at=article.published_at,
                    tl_dr=article.raw_title[:140],
                    summary=article.raw_description or article.raw_content or '',
                    why_it_matters='Content is being processed.',
                    badges=[],
                    tags=[],
                    references=[Reference(label="Source", url=article.raw_link)],
                    snippet=article.raw_description or '',
                    synthesis_failed=False
                )
        except Exception as e:
            print(f"Error getting article: {e}")
            return None
    
    def get_recent_articles(self, limit: int = 10, days: Optional[int] = None, exclude_hacker_news: bool = False) -> List[Card]:
        """Get recent articles with optional date filter (with smart fallback logic)
        
        Args:
            limit: Maximum number of articles to return
            days: Optional date filter (last N days)
            exclude_hacker_news: If True, exclude Hacker News articles (only applies to last resort tier)
        """
        try:
            with self.get_session() as session:
                # Build base query
                base_query = session.query(Article)
                if days:
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    base_query = base_query.filter(Article.published_at >= cutoff_date)
                
                # Try 1: Fully processed articles (best quality)
                # Order by relevance_score DESC, then published_at DESC (highest quality first)
                filters_try1 = [
                    Article.is_relevance_check_done == True,
                    Article.is_summarized == True,
                    Article.is_relevant == True
                ]
                
                query = base_query.filter(and_(*filters_try1)).order_by(desc(Article.relevance_score), desc(Article.published_at))
                articles = query.limit(limit).all()
                
                if articles:
                    return [card for article in articles if (card := article.to_card()) is not None]
                
                # Try 2: Relevance-checked and marked relevant (even if not summarized yet)
                # Order by relevance_score DESC, then published_at DESC
                filters_try2 = [
                    Article.is_relevance_check_done == True,
                    Article.is_relevant == True
                ]
                
                query = base_query.filter(and_(*filters_try2)).order_by(desc(Article.relevance_score), desc(Article.published_at))
                articles = query.limit(limit).all()
                
                if articles:
                    cards = []
                    for article in articles:
                        # If summarized, use the summarized card, otherwise create basic card
                        if article.is_summarized:
                            card = article.to_card()
                            if card:
                                cards.append(card)
                        else:
                            # Convert to cards using raw data (create basic cards)
                            cards.append(Card(
                                content_id=article.content_id,
                                type=article.type or 'blog',
                                title=article.raw_title,
                                source=article.source,
                                published_at=article.published_at,
                                tl_dr=article.raw_title[:140],
                                summary=article.raw_description or article.raw_content or '',
                                why_it_matters='Content is being processed.',
                                badges=[],
                                tags=[],
                                references=[Reference(label="Source", url=article.raw_link)],
                                snippet=article.raw_description or '',
                                synthesis_failed=False
                            ))
                    if cards:
                        return cards
                
                # Try 3: Any articles with raw data (last resort)
                # Note: Summarized articles are not possible here because summarization only happens
                # for relevance-checked and relevant articles, which would have been caught in Try 2
                # Apply additional quality filters to ensure relevance even in last resort
                filters = [
                    Article.raw_title != None,
                    Article.raw_title != '',
                    # Minimum title length to avoid spam/very short titles
                    func.length(Article.raw_title) >= 10,
                    # Must have either description or content with some substance
                    or_(
                        and_(Article.raw_description != None, func.length(Article.raw_description) >= 50),
                        and_(Article.raw_content != None, func.length(Article.raw_content) >= 100)
                    )
                ]
                
                filters.append(Article.source != 'Hacker News')
                
                query = base_query.filter(and_(*filters)).order_by(desc(Article.published_at))
                articles = query.limit(limit).all()
                
                if articles:
                    cards = []
                    for article in articles:
                        cards.append(Card(
                            content_id=article.content_id,
                            type=article.type or 'blog',
                            title=article.raw_title,
                            source=article.source,
                            published_at=article.published_at,
                            tl_dr=article.raw_title[:140],
                            summary=article.raw_description or article.raw_content or '',
                            why_it_matters='Content is being processed.',
                            badges=[],
                            tags=[],
                            references=[Reference(label="Source", url=article.raw_link)],
                            snippet=article.raw_description or '',
                            synthesis_failed=False
                        ))
                    return cards
                
                return []
        except Exception as e:
            print(f"Error getting recent articles: {e}")
            return []
    
    def search_articles(self, query: str, limit: int = 15, days: Optional[int] = None) -> List[Card]:
        """Search articles by title and summary (with smart fallback logic)"""
        try:
            with self.get_session() as session:
                search_filter = or_(
                    Article.title.ilike(f'%{query}%'),
                    Article.summary.ilike(f'%{query}%'),
                    Article.tl_dr.ilike(f'%{query}%'),
                    Article.raw_title.ilike(f'%{query}%'),  # Also search raw title
                    Article.raw_description.ilike(f'%{query}%'),
                    Article.raw_content.ilike(f'%{query}%')
                )
                
                base_query = session.query(Article).filter(search_filter)
                if days:
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    base_query = base_query.filter(Article.published_at >= cutoff_date)
                
                # Try 1: Fully processed articles
                db_query = base_query.filter(
                    and_(
                        Article.is_relevance_check_done == True,
                        Article.is_summarized == True,
                        Article.is_relevant == True
                    )
                )
                articles = db_query.order_by(desc(Article.published_at)).limit(limit).all()
                
                if articles:
                    return [card for article in articles if (card := article.to_card()) is not None]
                
                # Try 2: Relevance-checked and marked relevant (preferred over just summarized)
                db_query = base_query.filter(
                    and_(
                        Article.is_relevance_check_done == True,
                        Article.is_relevant == True
                    )
                )
                articles = db_query.order_by(desc(Article.published_at)).limit(limit).all()
                
                if articles:
                    cards = []
                    for article in articles:
                        if article.is_summarized:
                            card = article.to_card()
                            if card:
                                cards.append(card)
                        else:
                            cards.append(Card(
                                content_id=article.content_id,
                                type=article.type or 'blog',
                                title=article.raw_title,
                                source=article.source,
                                published_at=article.published_at,
                                tl_dr=article.raw_title[:140],
                                summary=article.raw_description or article.raw_content or '',
                                why_it_matters='Content is being processed.',
                                badges=[],
                                tags=[],
                                references=[Reference(label="Source", url=article.raw_link)],
                                snippet=article.raw_description or '',
                                synthesis_failed=False
                            ))
                    if cards:
                        return cards
                
                # Try 3: Raw articles matching search
                # Note: Summarized articles are not possible here because summarization only happens
                # for relevance-checked and relevant articles, which would have been caught in Try 2
                articles = base_query.filter(
                    and_(
                        Article.raw_title != None,
                        Article.raw_title != ''
                    )
                ).order_by(desc(Article.published_at)).limit(limit).all()
                
                if articles:
                    cards = []
                    for article in articles:
                        cards.append(Card(
                            content_id=article.content_id,
                            type=article.type or 'blog',
                            title=article.raw_title,
                            source=article.source,
                            published_at=article.published_at,
                            tl_dr=article.raw_title[:140],
                            summary=article.raw_description or article.raw_content or '',
                            why_it_matters='Content is being processed.',
                            badges=[],
                            tags=[],
                            references=[Reference(label="Source", url=article.raw_link)],
                            snippet=article.raw_description or '',
                            synthesis_failed=False
                        ))
                    return cards
                
                return []
        except Exception as e:
            print(f"Error searching articles: {e}")
            return []
    
    def get_articles_by_type(self, content_type: str, limit: int = 10) -> List[Card]:
        """Get articles by type (with smart fallback logic)"""
        try:
            with self.get_session() as session:
                base_query = session.query(Article).filter(Article.type == content_type)
                
                # Try 1: Fully processed
                articles = base_query.filter(
                    and_(
                        Article.is_relevance_check_done == True,
                        Article.is_summarized == True,
                        Article.is_relevant == True
                    )
                ).order_by(desc(Article.published_at)).limit(limit).all()
                
                if articles:
                    return [card for article in articles if (card := article.to_card()) is not None]
                
                # Try 2: Relevance-checked and marked relevant (preferred over just summarized)
                articles = base_query.filter(
                    and_(
                        Article.is_relevance_check_done == True,
                        Article.is_relevant == True
                    )
                ).order_by(desc(Article.published_at)).limit(limit).all()
                
                if articles:
                    cards = []
                    for article in articles:
                        if article.is_summarized:
                            card = article.to_card()
                            if card:
                                cards.append(card)
                        else:
                            cards.append(Card(
                                content_id=article.content_id,
                                type=article.type or 'blog',
                                title=article.raw_title,
                                source=article.source,
                                published_at=article.published_at,
                                tl_dr=article.raw_title[:140],
                                summary=article.raw_description or article.raw_content or '',
                                why_it_matters='Content is being processed.',
                                badges=[],
                                tags=[],
                                references=[Reference(label="Source", url=article.raw_link)],
                                snippet=article.raw_description or '',
                                synthesis_failed=False
                            ))
                    if cards:
                        return cards
                
                # Try 3: Any with that type (with raw data)
                # Note: Summarized articles are not possible here because summarization only happens
                # for relevance-checked and relevant articles, which would have been caught in Try 2
                articles = base_query.filter(
                    and_(
                        Article.raw_title != None,
                        Article.raw_title != ''
                    )
                ).order_by(desc(Article.published_at)).limit(limit).all()
                
                if articles:
                    cards = []
                    for article in articles:
                        if article.is_summarized:
                            card = article.to_card()
                            if card:
                                cards.append(card)
                        else:
                            # Create basic card from raw data
                            cards.append(Card(
                                content_id=article.content_id,
                                type=article.type or 'blog',
                                title=article.raw_title,
                                source=article.source,
                                published_at=article.published_at,
                                tl_dr=article.raw_title[:140],
                                summary=article.raw_description or article.raw_content or '',
                                why_it_matters='Content is being processed.',
                                badges=[],
                                tags=[],
                                references=[Reference(label="Source", url=article.raw_link)],
                                snippet=article.raw_description or '',
                                synthesis_failed=False
                            ))
                    return cards
                
                return []
        except Exception as e:
            print(f"Error getting articles by type: {e}")
            return []
    
    def get_article_count(self) -> int:
        """Get total article count"""
        try:
            with self.get_session() as session:
                return session.query(Article).count()
        except Exception as e:
            print(f"Error getting article count: {e}")
            return 0
    
    def cleanup_old_articles(self, days: int = 90) -> int:
        """Remove articles older than specified days"""
        try:
            with self.get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                deleted_count = session.query(Article).filter(
                    Article.published_at < cutoff_date
                ).delete()
                session.commit()
                return deleted_count
        except Exception as e:
            print(f"Error cleaning up old articles: {e}")
            return 0

    def clear_all_articles(self) -> int:
        """Clear all articles from the database and vector index"""
        try:
            with self.get_session() as session:
                deleted_count = session.query(Article).delete()
                session.commit()
                print(f"Cleared {deleted_count} articles from database")
                
                # Also clear the vector index
                try:
                    from backend.vector_store import vector_store
                    vector_store.clear_all_documents()
                except Exception as e:
                    print(f"Warning: Could not clear vector index: {e}")
                
                return deleted_count
        except Exception as e:
            print(f"Error clearing all articles: {e}")
            return 0
    
    def insert_raw_article(self, raw_article: Dict[str, Any]) -> bool:
        """Insert raw article data (before summarization)"""
        try:
            with self.get_session() as session:
                # Check if article already exists
                existing = session.query(Article).filter(
                    Article.content_id == raw_article['content_id']
                ).first()
                
                if existing:
                    return False  # Already exists
                
                # Create new raw article
                # For old databases with NOT NULL constraints, provide default values for old columns
                article = Article(
                    content_id=raw_article['content_id'],
                    raw_title=raw_article['title'],
                    raw_description=raw_article.get('description', ''),
                    raw_content=raw_article.get('content', ''),
                    raw_link=raw_article['link'],
                    source=raw_article['source'],
                    published_at=raw_article['published_at'],
                    is_relevance_check_done=False,
                    is_summarized=False,
                    failure_count=0,
                    is_relevant=None,  # Not checked yet
                    # Provide defaults for old NOT NULL columns (for backward compatibility)
                    type='blog',  # Default type for raw articles (will be updated during summarization)
                    title=raw_article['title'],  # Use raw_title as title initially
                    tl_dr=raw_article['title'][:140] if raw_article.get('title') else '',  # Temporary TL;DR
                    summary=raw_article.get('description', '')[:500] if raw_article.get('description') else '',
                    why_it_matters='',  # Will be filled during summarization
                    badges=[],
                    tags=[],
                    references=[]
                )
                session.add(article)
                session.commit()
                return True
        except Exception as e:
            print(f"Error inserting raw article: {e}")
            return False
    
    def get_unsummarized_articles(self, limit: int = None) -> List[Article]:
        """Get articles that haven't been summarized yet (and haven't failed too many times).
        Prioritizes highest relevance scores first."""
        try:
            with self.get_session() as session:
                query = session.query(Article).filter(
                    and_(
                        Article.is_summarized == False,
                        Article.is_relevance_check_done == True,
                        Article.is_relevant == True,  # Only relevant articles
                        Article.failure_count < 3  # Don't retry if failed 3+ times
                    )
                ).order_by(desc(Article.relevance_score), desc(Article.published_at))  # Prioritize highest scores first
                
                if limit:
                    query = query.limit(limit)
                
                return query.all()
        except Exception as e:
            print(f"Error getting unsummarized articles: {e}")
            return []
    
    def get_unchecked_relevance_articles(self, limit: int = None) -> List[Article]:
        """Get articles that haven't had relevance check done yet.
        Prioritizes most recently published articles."""
        try:
            with self.get_session() as session:
                query = session.query(Article).filter(
                    and_(
                        Article.is_relevance_check_done == False,
                        Article.failure_count < 3  # Don't retry if failed 3+ times
                    )
                ).order_by(desc(Article.published_at))  # Prioritize most recently published
                
                if limit:
                    query = query.limit(limit)
                
                return query.all()
        except Exception as e:
            print(f"Error getting unchecked relevance articles: {e}")
            return []
    
    def update_relevance_check(self, content_id: str, is_relevant: bool, relevance_score: Optional[float] = None, increment_failure: bool = False) -> bool:
        """Update article with relevance check result and score"""
        try:
            with self.get_session() as session:
                article = session.query(Article).filter(
                    Article.content_id == content_id
                ).first()
                
                if not article:
                    return False
                
                article.is_relevance_check_done = True
                article.is_relevant = is_relevant
                if relevance_score is not None:
                    article.relevance_score = relevance_score
                if increment_failure:
                    article.failure_count += 1
                else:
                    # Reset failure count on success
                    article.failure_count = 0
                
                session.commit()
                return True
        except Exception as e:
            print(f"Error updating relevance check: {e}")
            return False
    
    def increment_summarization_failure(self, content_id: str) -> bool:
        """Increment failure count for summarization attempts"""
        try:
            with self.get_session() as session:
                article = session.query(Article).filter(
                    Article.content_id == content_id
                ).first()
                
                if not article:
                    return False
                
                article.failure_count += 1
                session.commit()
                return True
        except Exception as e:
            print(f"Error incrementing summarization failure: {e}")
            return False
    
    def update_article_summary(self, content_id: str, card: Card) -> bool:
        """Update article with summarized data"""
        try:
            with self.get_session() as session:
                article = session.query(Article).filter(
                    Article.content_id == content_id
                ).first()
                
                if not article:
                    return False
                
                # Update with summarized data
                article.is_summarized = True
                # Reset failure count on successful summarization
                article.failure_count = 0
                article.type = card.type
                article.title = card.title
                article.tl_dr = card.tl_dr
                article.summary = card.summary
                article.why_it_matters = card.why_it_matters
                article.badges = card.badges
                article.tags = card.tags
                article.references = [ref.dict() for ref in card.references]
                article.snippet = card.snippet
                article.synthesis_failed = card.synthesis_failed
                article.summarized_at = datetime.utcnow()
                
                session.commit()
                return True
        except Exception as e:
            print(f"Error updating article summary: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()
