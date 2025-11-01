from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

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
    
    @field_validator('tl_dr')
    @classmethod
    def validate_tl_dr(cls, v):
        if len(v) > 140:
            raise ValueError('TL;DR must be 140 characters or less')
        return v
    
    @field_validator('badges')
    @classmethod
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
    
    # Raw article data (saved immediately after extraction)
    raw_title = Column(String(500), nullable=False)
    raw_description = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    raw_link = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    
    # Processing status flags
    is_relevance_check_done = Column(Boolean, default=False, nullable=False, index=True)
    is_summarized = Column(Boolean, default=False, nullable=False, index=True)
    failure_count = Column(Integer, default=0, nullable=False)  # Track failures, don't retry if > 3
    is_relevant = Column(Boolean, nullable=True)  # Result of relevance check
    relevance_score = Column(Float, nullable=True, index=True)  # LLM relevance score (0.0-1.0)
    
    # Summarized data (filled after AI processing)
    type = Column(String(50), nullable=True)  # paper, blog, release
    title = Column(String(500), nullable=True)  # May differ from raw_title after processing
    tl_dr = Column(String(140), nullable=True)
    summary = Column(Text, nullable=True)
    why_it_matters = Column(Text, nullable=True)
    badges = Column(JSON, nullable=True, default=list)  # List of strings
    tags = Column(JSON, nullable=True, default=list)    # List of strings
    references = Column(JSON, nullable=True, default=list)  # List of Reference objects
    snippet = Column(Text, nullable=True)
    synthesis_failed = Column(Boolean, default=False)
    
    ingested_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    summarized_at = Column(DateTime, nullable=True)
    
    def to_card(self) -> Optional[Card]:
        """Convert database model to API model"""
        # Only return Card if article is summarized
        if not self.is_summarized:
            return None
        
        return Card(
            content_id=self.content_id,
            type=self.type or 'blog',
            title=self.title or self.raw_title,
            source=self.source,
            published_at=self.published_at,
            tl_dr=self.tl_dr or self.raw_title[:140],
            summary=self.summary or self.raw_description or '',
            why_it_matters=self.why_it_matters or '',
            badges=self.badges or [],
            tags=self.tags or [],
            references=[Reference(**ref) for ref in (self.references or [])],
            snippet=self.snippet,
            synthesis_failed=self.synthesis_failed
        )
    
    @classmethod
    def from_card(cls, card: Card) -> 'Article':
        """Create database model from API model (for already summarized articles)"""
        return cls(
            content_id=card.content_id,
            raw_title=card.title,
            raw_description='',
            raw_content='',
            raw_link='',
            source=card.source,
            published_at=card.published_at,
            is_summarized=True,
            type=card.type,
            title=card.title,
            tl_dr=card.tl_dr,
            summary=card.summary,
            why_it_matters=card.why_it_matters,
            badges=card.badges,
            tags=card.tags,
            references=[ref.dict() for ref in card.references],
            snippet=card.snippet,
            synthesis_failed=card.synthesis_failed,
            summarized_at=datetime.utcnow()
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
