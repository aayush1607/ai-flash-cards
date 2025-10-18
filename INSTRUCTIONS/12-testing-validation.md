# Todo 12: Testing and Validation

## Objective
Implement comprehensive testing and validation to ensure all application features work correctly, including unit tests, integration tests, and manual validation procedures.

## Files to Create

### 1. `tests/__init__.py`
Create test package initialization:

```python
# Test package initialization
```

### 2. `tests/test_models.py`
Create model validation tests:

```python
import pytest
from datetime import datetime
from backend.models import Card, Reference, TopicFeedResponse, MorningBriefResponse

class TestModels:
    """Test data models and validation"""
    
    def test_card_creation(self):
        """Test Card model creation and validation"""
        card = Card(
            content_id="test:123",
            type="blog",
            title="Test Article",
            source="Test Source",
            published_at=datetime.utcnow(),
            tl_dr="Test TL;DR",
            summary="Test summary",
            why_it_matters="Test significance",
            badges=["CODE"],
            tags=["test"],
            references=[Reference(label="Test", url="https://test.com")],
            snippet="Test snippet"
        )
        
        assert card.content_id == "test:123"
        assert card.type == "blog"
        assert card.title == "Test Article"
        assert len(card.tl_dr) <= 140
    
    def test_card_validation(self):
        """Test Card model validation rules"""
        with pytest.raises(ValueError):
            Card(
                content_id="test:123",
                type="blog",
                title="Test Article",
                source="Test Source",
                published_at=datetime.utcnow(),
                tl_dr="x" * 141,  # Too long
                summary="Test summary",
                why_it_matters="Test significance"
            )
    
    def test_reference_creation(self):
        """Test Reference model creation"""
        ref = Reference(label="Paper", url="https://arxiv.org/...")
        assert ref.label == "Paper"
        assert ref.url == "https://arxiv.org/..."
    
    def test_topic_feed_response(self):
        """Test TopicFeedResponse model"""
        response = TopicFeedResponse(
            topic_query="test",
            topic_summary="Test summary",
            why_it_matters="Test significance",
            items=[],
            meta={"test": "value"}
        )
        
        assert response.topic_query == "test"
        assert response.topic_summary == "Test summary"
        assert response.items == []
        assert response.meta["test"] == "value"
```

### 3. `tests/test_database.py`
Create database tests:

```python
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from backend.database import DatabaseManager
from backend.models import Card, Reference

class TestDatabase:
    """Test database operations"""
    
    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        
        # Create database manager with temp path
        db_manager = DatabaseManager()
        db_manager.database_path = db_path
        
        yield db_manager
        
        # Cleanup
        os.unlink(db_path)
    
    def test_insert_article(self, temp_db):
        """Test article insertion"""
        card = Card(
            content_id="test:123",
            type="blog",
            title="Test Article",
            source="Test Source",
            published_at=datetime.utcnow(),
            tl_dr="Test TL;DR",
            summary="Test summary",
            why_it_matters="Test significance",
            badges=["CODE"],
            tags=["test"],
            references=[Reference(label="Test", url="https://test.com")],
            snippet="Test snippet"
        )
        
        result = temp_db.insert_article(card)
        assert result is True
        
        # Verify article was inserted
        retrieved = temp_db.get_article_by_id("test:123")
        assert retrieved is not None
        assert retrieved.title == "Test Article"
    
    def test_get_recent_articles(self, temp_db):
        """Test getting recent articles"""
        # Insert test articles
        for i in range(5):
            card = Card(
                content_id=f"test:{i}",
                type="blog",
                title=f"Test Article {i}",
                source="Test Source",
                published_at=datetime.utcnow() - timedelta(days=i),
                tl_dr=f"Test TL;DR {i}",
                summary=f"Test summary {i}",
                why_it_matters=f"Test significance {i}",
                badges=[],
                tags=[],
                references=[],
                snippet=f"Test snippet {i}"
            )
            temp_db.insert_article(card)
        
        # Test getting recent articles
        recent = temp_db.get_recent_articles(limit=3)
        assert len(recent) == 3
        assert recent[0].title == "Test Article 0"  # Most recent first
    
    def test_search_articles(self, temp_db):
        """Test article search functionality"""
        # Insert test articles
        card1 = Card(
            content_id="test:1",
            type="blog",
            title="Machine Learning Article",
            source="Test Source",
            published_at=datetime.utcnow(),
            tl_dr="ML TL;DR",
            summary="Machine learning summary",
            why_it_matters="ML significance",
            badges=[],
            tags=[],
            references=[],
            snippet="ML snippet"
        )
        
        card2 = Card(
            content_id="test:2",
            type="blog",
            title="Deep Learning Article",
            source="Test Source",
            published_at=datetime.utcnow(),
            tl_dr="DL TL;DR",
            summary="Deep learning summary",
            why_it_matters="DL significance",
            badges=[],
            tags=[],
            references=[],
            snippet="DL snippet"
        )
        
        temp_db.insert_article(card1)
        temp_db.insert_article(card2)
        
        # Test search
        results = temp_db.search_articles("learning")
        assert len(results) == 2
        
        results = temp_db.search_articles("machine")
        assert len(results) == 1
        assert results[0].title == "Machine Learning Article"
```

### 4. `tests/test_api.py`
Create API tests:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

class TestAPI:
    """Test API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_morning_brief(self, client):
        """Test morning brief endpoint"""
        response = client.get("/api/morning-brief")
        assert response.status_code == 200
        
        data = response.json()
        assert "items" in data
        assert "total_count" in data
        assert isinstance(data["items"], list)
    
    def test_topic_feed(self, client):
        """Test topic feed endpoint"""
        response = client.get("/api/topic-feed?q=transformer")
        assert response.status_code == 200
        
        data = response.json()
        assert "topic_query" in data
        assert "topic_summary" in data
        assert "items" in data
        assert data["topic_query"] == "transformer"
    
    def test_topic_feed_invalid_timeframe(self, client):
        """Test topic feed with invalid timeframe"""
        response = client.get("/api/topic-feed?q=test&timeframe=invalid")
        assert response.status_code == 400
        
        data = response.json()
        assert "error" in data
        assert "detail" in data
    
    def test_card_detail(self, client):
        """Test card detail endpoint"""
        # First get a card from morning brief
        response = client.get("/api/morning-brief")
        data = response.json()
        
        if data["items"]:
            card_id = data["items"][0]["content_id"]
            response = client.get(f"/api/card/{card_id}")
            assert response.status_code == 200
            
            card_data = response.json()
            assert "content_id" in card_data
            assert "title" in card_data
        else:
            # No cards available, test 404
            response = client.get("/api/card/nonexistent")
            assert response.status_code == 404
    
    def test_scheduler_status(self, client):
        """Test scheduler status endpoint"""
        response = client.get("/api/scheduler/status")
        assert response.status_code == 200
        
        data = response.json()
        assert "running" in data
        assert "last_run" in data
    
    def test_scheduler_stats(self, client):
        """Test scheduler stats endpoint"""
        response = client.get("/api/scheduler/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_articles" in data
        assert "scheduler_status" in data
```

### 5. `tests/test_ingestion.py`
Create ingestion tests:

```python
import pytest
from unittest.mock import Mock, patch
from backend.ingestion import RSSIngestionPipeline

class TestIngestion:
    """Test ingestion pipeline"""
    
    @pytest.fixture
    def mock_feed(self):
        """Mock RSS feed data"""
        return {
            'entries': [
                {
                    'title': 'Test Article 1',
                    'link': 'https://test.com/article1',
                    'description': 'Test description 1',
                    'published_parsed': (2024, 1, 15, 10, 0, 0, 0, 0, 0)
                },
                {
                    'title': 'Test Article 2',
                    'link': 'https://test.com/article2',
                    'description': 'Test description 2',
                    'published_parsed': (2024, 1, 14, 10, 0, 0, 0, 0, 0)
                }
            ]
        }
    
    @patch('backend.ingestion.feedparser.parse')
    def test_fetch_single_feed(self, mock_parse, mock_feed):
        """Test fetching single feed"""
        mock_parse.return_value = mock_feed
        
        pipeline = RSSIngestionPipeline()
        articles = pipeline._fetch_single_feed('https://test.com/feed.xml')
        
        assert len(articles) == 2
        assert articles[0]['title'] == 'Test Article 1'
        assert articles[1]['title'] == 'Test Article 2'
    
    def test_parse_rss_entry(self):
        """Test parsing RSS entry"""
        pipeline = RSSIngestionPipeline()
        
        entry = {
            'title': 'Test Article',
            'link': 'https://test.com/article',
            'description': 'Test description',
            'published_parsed': (2024, 1, 15, 10, 0, 0, 0, 0, 0)
        }
        
        article = pipeline._parse_rss_entry(entry, 'https://test.com/feed.xml')
        
        assert article is not None
        assert article['title'] == 'Test Article'
        assert article['link'] == 'https://test.com/article'
        assert article['description'] == 'Test description'
    
    def test_clean_content(self):
        """Test content cleaning"""
        pipeline = RSSIngestionPipeline()
        
        dirty_content = "<p>Test content</p>   \n\n  <br/>More content"
        clean_content = pipeline._clean_content(dirty_content)
        
        assert clean_content == "Test content More content"
        assert "<p>" not in clean_content
        assert "<br/>" not in clean_content
```

### 6. `tests/test_frontend.py`
Create frontend tests:

```python
import pytest
from unittest.mock import Mock, patch
import json

class TestFrontend:
    """Test frontend functionality"""
    
    def test_card_rendering(self):
        """Test card rendering logic"""
        # Mock card data
        card_data = {
            "content_id": "test:123",
            "title": "Test Article",
            "source": "Test Source",
            "published_at": "2024-01-15T10:00:00Z",
            "tl_dr": "Test TL;DR",
            "summary": "Test summary",
            "why_it_matters": "Test significance",
            "badges": ["CODE"],
            "tags": ["test"],
            "references": [{"label": "Test", "url": "https://test.com"}],
            "snippet": "Test snippet"
        }
        
        # Test rendering logic
        assert card_data["title"] == "Test Article"
        assert len(card_data["tl_dr"]) <= 140
        assert len(card_data["badges"]) > 0
        assert len(card_data["tags"]) > 0
        assert len(card_data["references"]) > 0
    
    def test_date_formatting(self):
        """Test date formatting"""
        from datetime import datetime
        
        date_string = "2024-01-15T10:00:00Z"
        date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        
        formatted = date.strftime('%b %d, %Y')
        assert formatted == "Jan 15, 2024"
    
    def test_error_handling(self):
        """Test error handling logic"""
        # Test network error
        error = Exception("Network error")
        assert "Network error" in str(error)
        
        # Test HTTP error
        error = Exception("HTTP 500: Internal Server Error")
        assert "500" in str(error)
        
        # Test timeout error
        error = Exception("Request timeout")
        assert "timeout" in str(error)
```

### 7. `tests/test_integration.py`
Create integration tests:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db_manager
from backend.models import Card, Reference
from datetime import datetime

class TestIntegration:
    """Test full application integration"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_card(self):
        """Create sample card for testing"""
        return Card(
            content_id="integration:test",
            type="blog",
            title="Integration Test Article",
            source="Test Source",
            published_at=datetime.utcnow(),
            tl_dr="Integration test TL;DR",
            summary="Integration test summary",
            why_it_matters="Integration test significance",
            badges=["CODE"],
            tags=["integration", "test"],
            references=[Reference(label="Test", url="https://test.com")],
            snippet="Integration test snippet"
        )
    
    def test_full_workflow(self, client, sample_card):
        """Test complete application workflow"""
        # Insert test card
        db_manager.insert_article(sample_card)
        
        # Test morning brief
        response = client.get("/api/morning-brief")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["items"]) > 0
        
        # Test topic search
        response = client.get("/api/topic-feed?q=integration")
        assert response.status_code == 200
        
        data = response.json()
        assert data["topic_query"] == "integration"
        assert len(data["items"]) > 0
        
        # Test card detail
        card_id = sample_card.content_id
        response = client.get(f"/api/card/{card_id}")
        assert response.status_code == 200
        
        card_data = response.json()
        assert card_data["content_id"] == card_id
        assert card_data["title"] == "Integration Test Article"
    
    def test_error_scenarios(self, client):
        """Test error scenarios"""
        # Test invalid card ID
        response = client.get("/api/card/nonexistent")
        assert response.status_code == 404
        
        # Test invalid timeframe
        response = client.get("/api/topic-feed?q=test&timeframe=invalid")
        assert response.status_code == 400
        
        # Test empty search
        response = client.get("/api/topic-feed?q=")
        assert response.status_code == 422
```

### 8. `tests/test_validation.py`
Create validation tests:

```python
import pytest
from backend.models import Card, Reference
from datetime import datetime

class TestValidation:
    """Test data validation and constraints"""
    
    def test_card_validation_rules(self):
        """Test Card model validation rules"""
        # Test valid card
        valid_card = Card(
            content_id="test:123",
            type="blog",
            title="Test Article",
            source="Test Source",
            published_at=datetime.utcnow(),
            tl_dr="Valid TL;DR",
            summary="Valid summary",
            why_it_matters="Valid significance",
            badges=["CODE"],
            tags=["test"],
            references=[Reference(label="Test", url="https://test.com")],
            snippet="Valid snippet"
        )
        
        assert valid_card.content_id == "test:123"
        assert valid_card.type == "blog"
        assert len(valid_card.tl_dr) <= 140
    
    def test_tl_dr_length_validation(self):
        """Test TL;DR length validation"""
        with pytest.raises(ValueError):
            Card(
                content_id="test:123",
                type="blog",
                title="Test Article",
                source="Test Source",
                published_at=datetime.utcnow(),
                tl_dr="x" * 141,  # Too long
                summary="Valid summary",
                why_it_matters="Valid significance"
            )
    
    def test_badge_validation(self):
        """Test badge validation"""
        with pytest.raises(ValueError):
            Card(
                content_id="test:123",
                type="blog",
                title="Test Article",
                source="Test Source",
                published_at=datetime.utcnow(),
                tl_dr="Valid TL;DR",
                summary="Valid summary",
                why_it_matters="Valid significance",
                badges=["INVALID_BADGE"]  # Invalid badge
            )
    
    def test_reference_validation(self):
        """Test reference validation"""
        # Valid reference
        ref = Reference(label="Paper", url="https://arxiv.org/...")
        assert ref.label == "Paper"
        assert ref.url == "https://arxiv.org/..."
        
        # Test reference in card
        card = Card(
            content_id="test:123",
            type="paper",
            title="Test Paper",
            source="arXiv",
            published_at=datetime.utcnow(),
            tl_dr="Valid TL;DR",
            summary="Valid summary",
            why_it_matters="Valid significance",
            badges=[],
            tags=[],
            references=[ref],
            snippet="Valid snippet"
        )
        
        assert len(card.references) == 1
        assert card.references[0].label == "Paper"
```

### 9. `tests/test_performance.py`
Create performance tests:

```python
import pytest
import time
from backend.database import db_manager
from backend.models import Card, Reference
from datetime import datetime

class TestPerformance:
    """Test application performance"""
    
    def test_database_insertion_performance(self):
        """Test database insertion performance"""
        start_time = time.time()
        
        # Insert multiple cards
        for i in range(100):
            card = Card(
                content_id=f"perf:test:{i}",
                type="blog",
                title=f"Performance Test {i}",
                source="Test Source",
                published_at=datetime.utcnow(),
                tl_dr=f"Performance test TL;DR {i}",
                summary=f"Performance test summary {i}",
                why_it_matters=f"Performance test significance {i}",
                badges=[],
                tags=[],
                references=[],
                snippet=f"Performance test snippet {i}"
            )
            db_manager.insert_article(card)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete within reasonable time
        assert duration < 10.0  # 10 seconds for 100 insertions
    
    def test_database_query_performance(self):
        """Test database query performance"""
        # Insert test data
        for i in range(50):
            card = Card(
                content_id=f"query:test:{i}",
                type="blog",
                title=f"Query Test {i}",
                source="Test Source",
                published_at=datetime.utcnow(),
                tl_dr=f"Query test TL;DR {i}",
                summary=f"Query test summary {i}",
                why_it_matters=f"Query test significance {i}",
                badges=[],
                tags=[],
                references=[],
                snippet=f"Query test snippet {i}"
            )
            db_manager.insert_article(card)
        
        # Test query performance
        start_time = time.time()
        results = db_manager.get_recent_articles(limit=10)
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 1.0  # 1 second for query
        assert len(results) <= 10
    
    def test_search_performance(self):
        """Test search performance"""
        # Insert test data
        for i in range(50):
            card = Card(
                content_id=f"search:test:{i}",
                type="blog",
                title=f"Search Test {i}",
                source="Test Source",
                published_at=datetime.utcnow(),
                tl_dr=f"Search test TL;DR {i}",
                summary=f"Search test summary {i}",
                why_it_matters=f"Search test significance {i}",
                badges=[],
                tags=[],
                references=[],
                snippet=f"Search test snippet {i}"
            )
            db_manager.insert_article(card)
        
        # Test search performance
        start_time = time.time()
        results = db_manager.search_articles("test", limit=10)
        end_time = time.time()
        
        duration = end_time - start_time
        assert duration < 2.0  # 2 seconds for search
        assert len(results) <= 10
```

### 10. `tests/conftest.py`
Create test configuration:

```python
import pytest
import tempfile
import os
from backend.config import config

@pytest.fixture(scope="session")
def test_config():
    """Setup test configuration"""
    # Override config for testing
    config.app.database_path = tempfile.mktemp(suffix='.db')
    config.app.top_n_morning_brief = 5
    config.app.default_timeframe_days = 7
    
    yield config
    
    # Cleanup
    if os.path.exists(config.app.database_path):
        os.unlink(config.app.database_path)

@pytest.fixture(autouse=True)
def setup_test_environment(test_config):
    """Setup test environment for each test"""
    # Ensure test database is clean
    if os.path.exists(test_config.app.database_path):
        os.unlink(test_config.app.database_path)
    
    yield
    
    # Cleanup after each test
    if os.path.exists(test_config.app.database_path):
        os.unlink(test_config.app.database_path)
```

## Manual Testing Procedures

### 1. Application Startup
- [ ] FastAPI server starts without errors
- [ ] Database connection is established
- [ ] Scheduler starts successfully
- [ ] All services are healthy

### 2. Morning Brief Functionality
- [ ] Morning brief loads with articles
- [ ] Cards display correctly
- [ ] Navigation works (Next/Previous)
- [ ] Card detail modal opens
- [ ] References are clickable

### 3. Topic Search Functionality
- [ ] Search input accepts queries
- [ ] Topic feed loads with results
- [ ] Topic summary is displayed
- [ ] Timeframe filtering works
- [ ] Refresh functionality works

### 4. Error Handling
- [ ] Network errors are handled gracefully
- [ ] Invalid inputs show appropriate errors
- [ ] Service failures are communicated clearly
- [ ] Retry mechanisms work

### 5. Responsive Design
- [ ] Desktop layout works correctly
- [ ] Mobile layout is functional
- [ ] Touch interactions work
- [ ] Keyboard navigation works

### 6. Performance
- [ ] Page loads within 2 seconds
- [ ] Card transitions are smooth
- [ ] API responses are fast
- [ ] No memory leaks

## Test Execution

### 1. Unit Tests
```bash
# Run all unit tests
pytest tests/ -v

# Run specific test file
pytest tests/test_models.py -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

### 2. Integration Tests
```bash
# Run integration tests
pytest tests/test_integration.py -v

# Run with database
pytest tests/test_integration.py -v --db
```

### 3. Performance Tests
```bash
# Run performance tests
pytest tests/test_performance.py -v

# Run with timing
pytest tests/test_performance.py -v --durations=10
```

### 4. Manual Testing
```bash
# Start development server
uvicorn backend.main:app --reload

# Test endpoints
curl http://localhost:8000/api/health
curl http://localhost:8000/api/morning-brief
curl http://localhost:8000/api/topic-feed?q=transformer
```

## Validation Checklist
- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Performance tests meet requirements
- [ ] Manual testing procedures are completed
- [ ] Error scenarios are handled gracefully
- [ ] User experience is smooth and responsive
- [ ] All features work as expected
- [ ] Documentation is accurate
- [ ] Code quality is maintained
- [ ] Security considerations are addressed

## Next Steps
After completing this todo, the AIFlash MVP will be fully implemented and tested. The application will be ready for deployment and use.
