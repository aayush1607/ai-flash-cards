# AI Flash Cards

**Lightning-fast AI insights, sourced fresh daily.**

🌐 **[Live Demo](https://ai-flash-cards-master-6b09b9b.kuberns.cloud/)** - Try it now!

## 🎯 The Problem

The AI landscape is overwhelming. With hundreds of blogs, research papers, and news sources covering AI breakthroughs, it's nearly impossible to stay updated and identify what truly matters. Information overload makes it difficult to:

- **Stay ahead** of the latest AI developments
- **Filter signal from noise** in the vast AI content landscape  
- **Find relevant information** on specific AI topics quickly
- **Consume content efficiently** without spending hours reading

## 💡 The Solution

AI Flash Cards Service delivers latest news on AI breakthroughs & releases as swipeable cards. 

## 🔄 How It Works

```mermaid
graph TD
    A[RSS Feeds<br/>HuggingFace, OpenAI, HackerNews, Microsoft, Deepmind etc.] --> B[Content Mining<br/>Fetch & Parse Articles Data]
    B --> C[Filtering<br/>LLM-powered Relevance Check]
    C --> D[AI Summarization<br/>TL;DR, Summary, Why It Matters]
    D --> E[Vector Embeddings<br/>Azure OpenAI Embeddings]
    D --> F[Storage<br/>SQLite for fixed morning breif]
    E --> G[Vector DB<br/>Azure AI Search]
    F --> H[Morning Brief<br/>Top 10 Daily Cards]
    G --> I[Topic Search<br/>Semantic Search on Any Topic]
    H --> J[User Interface<br/>Swipeable Cards]
    I --> J
```

![AI Flash Cards Landing Page](img/landing.png)

### Daily Flow
1. **🌅 6 AM UTC**: Automated ingestion runs daily
2. **🤖 AI Processing**: Content filtered and summarized by AI
3. **📱 User Experience**: Fresh cards ready for morning consumption
4. **🔍 Search**: On-demand topic exploration anytime


It utilizes RSS feeds from trusted sources like Hugging Face, OpenAI, Hacker News, DeepMind, Microsoft, NVIDIA, AWS, arXiv, MIT.edu - fetches latest blogs, applies LLM powered filtering to figure out relevance and serves you the top 10 most relevant articles every day. Also provides search functionality to provide latest on any AI-related topic - this is done with help of semantic search on precomputed vectors on sources.

## Quick Start

### Prerequisites for development
- Python 3.11+
- Azure OpenAI service
- Azure AI Search service

### Local Development

1. **Clone and setup**:
   ```bash
   git clone <repo>
   cd AI-Flash-Cards
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

- `GET /api/morning-brief` - Daily top 10 most relevant AI articles as swipeable cards
- `GET /api/topic-feed?q={query}` - Semantic search for AI insights on any topic
- `GET /api/health` - System health check
- `GET /api/dev-stats` - Development statistics (dev only)

## Development

### Project Structure
```
AI-Flash-Cards/
├── backend/           # FastAPI application
├── frontend/         # Static web files (HTML/CSS/JS)
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
- **Daily Morning Brief**: Top 10 most relevant AI articles delivered as swipeable cards
- **Smart AI Filtering**: Automatically filters hundreds of AI sources to find relevance
- **Semantic Search**: Find relevant articles on any AI topic using vector search
- **AI-Powered Summaries**: Each card includes TL;DR, summary, and "why it matters"
- **Trusted Sources**: Content from Hugging Face, OpenAI, Hacker News, DeepMind, Microsoft, NVIDIA, AWS, arXiv, MIT.edu