# Todo 3: Backend Data Models and Database Schema

## Objective
Define Pydantic models for API contracts and SQLAlchemy models for database persistence, ensuring type safety and data validation throughout the application.

## Files to Create

### 1. `backend/models.py`
Create comprehensive data models:

```python
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json

# SQLAlchemy Base
Base = declarative_base()

# ============================================================================
# PYDANTIC MODELS (API Contracts)
# ============================================================================

class Reference(BaseModel):
    """Reference link model"""
    label: str = Field(..., description="Display label for the reference")
    url: str = Field(..., description="URL to the reference")

class Card(BaseModel):
    """Card model for API responses"""
    content_id: str = Field(..., description="Unique identifier for the content")
    type: str = Field(..., description="Content type: 'paper', 'blog', 'release'")
    title: str = Field(..., description="Article title")
    source: str = Field(..., description="Source publication")
    published_at: datetime = Field(..., description="Publication date")
    tl_dr: str = Field(..., max_length=140, description="One-sentence summary")
    summary: str = Field(..., description="2-3 sentence summary")
    why_it_matters: str = Field(..., description="Why this matters")
    badges: List[str] = Field(default_factory=list, description="Content badges")
    tags: List[str] = Field(default_factory=list, description="Topical tags")
    references: List[Reference] = Field(default_factory=list, description="Reference links")
    snippet: Optional[str] = Field(None, description="Content snippet")
    synthesis_failed: bool = Field(default=False, description="Whether AI synthesis failed")
    
    @validator('tl_dr')
    def validate_tl_dr(cls, v):
        if len(v) > 140:
            raise ValueError('TL;DR must be 140 characters or less')
        return v
    
    @validator('badges')
    def validate_badges(cls, v):
        allowed_badges = ['CODE', 'DATA', 'REPRO', 'BENCHMARK', 'TUTORIAL']
        for badge in v:
            if badge not in allowed_badges:
                raise ValueError(f'Invalid badge: {badge}. Allowed: {allowed_badges}')
        return v

class TopicFeedResponse(BaseModel):
    """Topic feed response model"""
    topic_query: str = Field(..., description="Original search query")
    topic_summary: str = Field(..., description="Synthesized topic summary")
    why_it_matters: str = Field(..., description="Why this topic matters")
    items: List[Card] = Field(..., description="Retrieved cards")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

class MorningBriefResponse(BaseModel):
    """Morning brief response model"""
    items: List[Card] = Field(..., description="Top N articles")
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Generation timestamp")
    total_count: int = Field(..., description="Total number of items")

# ============================================================================
# SQLALCHEMY MODELS (Database Schema)
# ============================================================================

class Article(Base):
    """Article database model"""
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content_id = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)  # paper, blog, release
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    tl_dr = Column(String(140), nullable=False)
    summary = Column(Text, nullable=False)
    why_it_matters = Column(Text, nullable=False)
    badges = Column(JSON, nullable=False, default=list)  # List of strings
    tags = Column(JSON, nullable=False, default=list)    # List of strings
    references = Column(JSON, nullable=False, default=list)  # List of Reference objects
    snippet = Column(Text, nullable=True)
    synthesis_failed = Column(Boolean, default=False)
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    def to_card(self) -> Card:
        """Convert database model to API model"""
        return Card(
            content_id=self.content_id,
            type=self.type,
            title=self.title,
            source=self.source,
            published_at=self.published_at,
            tl_dr=self.tl_dr,
            summary=self.summary,
            why_it_matters=self.why_it_matters,
            badges=self.badges or [],
            tags=self.tags or [],
            references=[Reference(**ref) for ref in (self.references or [])],
            snippet=self.snippet,
            synthesis_failed=self.synthesis_failed
        )
    
    @classmethod
    def from_card(cls, card: Card) -> 'Article':
        """Create database model from API model"""
        return cls(
            content_id=card.content_id,
            type=card.type,
            title=card.title,
            source=card.source,
            published_at=card.published_at,
            tl_dr=card.tl_dr,
            summary=card.summary,
            why_it_matters=card.why_it_matters,
            badges=card.badges,
            tags=card.tags,
            references=[ref.dict() for ref in card.references],
            snippet=card.snippet,
            synthesis_failed=card.synthesis_failed
        )

# ============================================================================
# DATABASE CONNECTION
# ============================================================================

def create_database_engine(database_path: str):
    """Create SQLAlchemy engine"""
    return create_engine(f"sqlite:///{database_path}", echo=False)

def create_tables(engine):
    """Create all database tables"""
    Base.metadata.create_all(engine)

def get_session_factory(engine):
    """Create session factory"""
    return sessionmaker(bind=engine)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_content_id(title: str, source: str, published_at: datetime) -> str:
    """Generate unique content ID"""
    # Format: source:type:hash
    import hashlib
    content_hash = hashlib.md5(f"{title}:{source}:{published_at}".encode()).hexdigest()[:8]
    return f"{source.lower()}:{content_hash}"

def detect_content_type(url: str, title: str) -> str:
    """Detect content type based on URL and title"""
    url_lower = url.lower()
    title_lower = title.lower()
    
    if 'arxiv.org' in url_lower or 'paper' in title_lower:
        return 'paper'
    elif 'github.com' in url_lower or 'code' in title_lower:
        return 'code'
    elif 'release' in title_lower or 'announce' in title_lower:
        return 'release'
    else:
        return 'blog'

def extract_badges(content: str, references: List[Reference]) -> List[str]:
    """Extract badges based on content analysis"""
    badges = []
    content_lower = content.lower()
    
    # Check for code references
    if any('github.com' in ref.url.lower() for ref in references):
        badges.append('CODE')
    
    # Check for dataset mentions
    if any(word in content_lower for word in ['dataset', 'data', 'benchmark']):
        badges.append('DATA')
    
    # Check for reproducibility
    if any(word in content_lower for word in ['reproduce', 'replication', 'open source']):
        badges.append('REPRO')
    
    return badges
```

### 2. `backend/database.py`
Create database connection and CRUD operations:

```python
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
        os.makedirs(os.path.dirname(config.app.database_path), exist_ok=True)
        
        # Create engine and tables
        self.engine = create_database_engine(config.app.database_path)
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
                    Article.title.contains(query),
                    Article.summary.contains(query),
                    Article.tl_dr.contains(query)
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

# Global database manager instance
db_manager = DatabaseManager()
```

## Key Features to Implement

### 1. Pydantic Models (API Contracts)
- **Card**: Complete article representation with validation
- **Reference**: Link structure with label and URL
- **TopicFeedResponse**: Search results with metadata
- **MorningBriefResponse**: Daily digest structure

### 2. SQLAlchemy Models (Database Schema)
- **Article**: Database table with all required fields
- **JSON fields**: For badges, tags, and references
- **Indexes**: On content_id and published_at for performance
- **Conversion methods**: to_card() and from_card() for API compatibility

### 3. Database Operations
- **CRUD operations**: Insert, read, update, delete
- **Search functionality**: Text search across title and summary
- **Date filtering**: Support for time-based queries
- **Type filtering**: Filter by content type
- **Cleanup**: Remove old articles

### 4. Data Validation
- **TL;DR length**: Enforce 140 character limit
- **Badge validation**: Only allow predefined badges
- **Content ID generation**: Unique identifier creation
- **Type detection**: Automatic content type classification

### 5. Utility Functions
- **Content ID generation**: MD5 hash based on title, source, date
- **Type detection**: Analyze URL and title for content type
- **Badge extraction**: Analyze content for relevant badges

## Database Schema

### Articles Table
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id VARCHAR(255) UNIQUE NOT NULL,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    source VARCHAR(200) NOT NULL,
    published_at DATETIME NOT NULL,
    tl_dr VARCHAR(140) NOT NULL,
    summary TEXT NOT NULL,
    why_it_matters TEXT NOT NULL,
    badges JSON NOT NULL DEFAULT '[]',
    tags JSON NOT NULL DEFAULT '[]',
    references JSON NOT NULL DEFAULT '[]',
    snippet TEXT,
    synthesis_failed BOOLEAN DEFAULT FALSE,
    ingested_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_content_id ON articles(content_id);
CREATE INDEX idx_published_at ON articles(published_at);
```

## Validation Checklist
- [ ] All Pydantic models have proper validation
- [ ] SQLAlchemy models match the database schema
- [ ] Conversion methods work between API and DB models
- [ ] Database operations handle errors gracefully
- [ ] Content ID generation creates unique identifiers
- [ ] Badge and type detection logic works correctly
- [ ] Database connection is properly configured
- [ ] All required indexes are created

## Next Steps
After completing this todo, proceed to "04-azure-integrations" to implement Azure AI Search and Azure OpenAI integrations.
