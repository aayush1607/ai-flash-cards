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
   cp env.example .env
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
├── test/             # Test suite
│   ├── unit/         # Unit tests
│   ├── integration/  # Integration tests
│   └── scripts/      # Utility scripts
├── data/            # SQLite database storage
├── INSTRUCTIONS/    # Implementation guides
└── requirements.txt  # Python dependencies
```

### Testing

Run the complete test suite:
```bash
python test/run_tests.py
```

Run specific test categories:
```bash
# Unit tests only
python test/run_unit_tests.py

# Integration tests only  
python test/run_integration_tests.py

# Utility scripts
python test/scripts/run_ingestion.py
```

### Key Features
- Daily Morning Brief (top 10 AI news)
- Topic-based search with semantic retrieval