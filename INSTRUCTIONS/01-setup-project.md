# Todo 1: Setup Project Structure

## Objective
Create the foundational project structure, dependencies, and configuration files for AIFlash MVP.

## Files to Create

### 1. `requirements.txt`
Create with the following dependencies:
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
openai==1.3.0
azure-search-documents==11.4.0
feedparser==6.0.10
schedule==1.2.0
python-dotenv==1.0.0
pydantic==2.5.0
sqlalchemy==2.0.23
python-multipart==0.0.6
aiofiles==23.2.1
```

### 2. `.env.example`
Create environment template:
```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME=text-embedding-3-large

# Azure AI Search Configuration
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_API_KEY=your-search-key
AZURE_SEARCH_INDEX_NAME=aiflash-index

# Application Settings
DATABASE_PATH=/data/aiflash.db
TOP_N_MORNING_BRIEF=10
DEFAULT_TIMEFRAME_DAYS=30
LOG_LEVEL=INFO

# RSS Feed Sources (comma-separated)
RSS_SOURCES=https://huggingface.co/blog/feed.xml,https://openai.com/news/rss.xml,https://hnrss.org/newest?q=AI
```

### 3. `README.md`
Create comprehensive setup documentation:
```markdown
# AIFlash MVP

AI Flash — research-grade AI breakthroughs & model releases, fast.

## Quick Start

### Prerequisites
- Python 3.11+
- Azure OpenAI service
- Azure AI Search service
- Azure Storage Account (for Azure Files)

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd AIFlash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

3. **Run the application**:
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the app**:
   - Frontend: http://localhost:8000
   - API docs: http://localhost:8000/docs

### Azure Deployment

1. **Create Azure resources**:
   - Azure OpenAI service
   - Azure AI Search service
   - Azure Storage Account with File Share
   - Azure Web App

2. **Configure Azure Web App**:
   - Set environment variables in App Settings
   - Mount Azure Files share to `/data` path
   - Deploy code via GitHub Actions or Azure CLI

3. **Initialize database**:
   ```bash
   # Run once to create tables and index
   python -m backend.database init
   ```

## Architecture

- **Backend**: FastAPI with SQLite + Azure AI Search
- **Frontend**: Vanilla JS + Tailwind CSS
- **AI**: Azure OpenAI for summarization and embeddings
- **Storage**: Azure Files for persistent SQLite database

## API Endpoints

- `GET /api/morning-brief` - Daily top AI news
- `GET /api/topic-feed?q={query}` - Search by topic
- `GET /api/ingest` - Manual ingestion trigger (dev only)

## Development

### Project Structure
```
AIFlash/
├── backend/           # FastAPI application
├── frontend/         # Static web files
├── data/            # SQLite database storage
├── INSTRUCTIONS/    # Implementation guides
└── requirements.txt  # Python dependencies
```

### Key Features
- Daily Morning Brief (top 10 AI news)
- Topic-based search with semantic retrieval
- Tinder-style card interface
- Keyboard navigation support
- Mobile-responsive design
```

## Validation Checklist
- [ ] All directories created (backend/, frontend/, data/, INSTRUCTIONS/)
- [ ] requirements.txt contains all necessary dependencies
- [ ] .env.example has all required environment variables
- [ ] README.md provides clear setup instructions
- [ ] .gitignore excludes sensitive files and build artifacts
- [ ] Project structure matches the plan

## Next Steps
After completing this todo, proceed to "02-backend-config" to implement the configuration system.
