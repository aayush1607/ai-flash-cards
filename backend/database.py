import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
from backend.config import config
from backend.models import Article, Card, create_database_engine, create_tables, get_session_factory

class DatabaseManager:
    """Database manager for CRUD operations"""
    
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(os.path.dirname(config.database_path), exist_ok=True)
        
        # Create engine and tables
        self.engine = create_database_engine(config.database_path)
        create_tables(self.engine)
        self.SessionLocal = get_session_factory(self.engine)
    
    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()
    
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
        """Get article by content ID"""
        try:
            with self.get_session() as session:
                article = session.query(Article).filter(
                    Article.content_id == content_id
                ).first()
                
                return article.to_card() if article else None
        except Exception as e:
            print(f"Error getting article: {e}")
            return None
    
    def get_recent_articles(self, limit: int = 10, days: Optional[int] = None) -> List[Card]:
        """Get recent articles with optional date filter"""
        try:
            with self.get_session() as session:
                query = session.query(Article).order_by(desc(Article.published_at))
                
                if days:
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    query = query.filter(Article.published_at >= cutoff_date)
                
                articles = query.limit(limit).all()
                return [article.to_card() for article in articles]
        except Exception as e:
            print(f"Error getting recent articles: {e}")
            return []
    
    def search_articles(self, query: str, limit: int = 15, days: Optional[int] = None) -> List[Card]:
        """Search articles by title and summary (basic text search)"""
        try:
            with self.get_session() as session:
                search_filter = or_(
                    Article.title.ilike(f'%{query}%'),
                    Article.summary.ilike(f'%{query}%'),
                    Article.tl_dr.ilike(f'%{query}%')
                )
                
                db_query = session.query(Article).filter(search_filter)
                
                if days:
                    cutoff_date = datetime.utcnow() - timedelta(days=days)
                    db_query = db_query.filter(Article.published_at >= cutoff_date)
                
                articles = db_query.order_by(desc(Article.published_at)).limit(limit).all()
                return [article.to_card() for article in articles]
        except Exception as e:
            print(f"Error searching articles: {e}")
            return []
    
    def get_articles_by_type(self, content_type: str, limit: int = 10) -> List[Card]:
        """Get articles by type"""
        try:
            with self.get_session() as session:
                articles = session.query(Article).filter(
                    Article.type == content_type
                ).order_by(desc(Article.published_at)).limit(limit).all()
                
                return [article.to_card() for article in articles]
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

# Global database manager instance
db_manager = DatabaseManager()
