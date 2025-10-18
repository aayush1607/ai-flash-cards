# Todo 2: Backend Configuration System

## Objective
Implement a robust configuration system that loads Azure credentials and application settings from environment variables with proper fallbacks and validation.

## Files to Create

### 1. `backend/config.py`
Create a comprehensive configuration module:

```python
import os
from typing import Optional
from pydantic import BaseSettings, Field
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AzureOpenAIConfig(BaseSettings):
    """Azure OpenAI configuration"""
    endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    api_version: str = Field(default="2024-02-15-preview", env="AZURE_OPENAI_API_VERSION")
    deployment_name: str = Field(..., env="AZURE_OPENAI_DEPLOYMENT_NAME")
    embedding_deployment_name: str = Field(..., env="AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

class AzureSearchConfig(BaseSettings):
    """Azure AI Search configuration"""
    endpoint: str = Field(..., env="AZURE_SEARCH_ENDPOINT")
    api_key: str = Field(..., env="AZURE_SEARCH_API_KEY")
    index_name: str = Field(..., env="AZURE_SEARCH_INDEX_NAME")

class AppConfig(BaseSettings):
    """Application configuration"""
    database_path: str = Field(default="./data/aiflash.db", env="DATABASE_PATH")
    top_n_morning_brief: int = Field(default=10, env="TOP_N_MORNING_BRIEF")
    default_timeframe_days: int = Field(default=30, env="DEFAULT_TIMEFRAME_DAYS")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    rss_sources: list[str] = Field(
        default_factory=lambda: [
            "https://huggingface.co/blog/feed.xml",
            "https://openai.com/news/rss.xml", 
            "https://hnrss.org/newest?q=AI"
        ],
        env="RSS_SOURCES"
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse comma-separated RSS sources if provided as string
        if isinstance(self.rss_sources, str):
            self.rss_sources = [s.strip() for s in self.rss_sources.split(",")]

class Config:
    """Main configuration container"""
    def __init__(self):
        self.azure_openai = AzureOpenAIConfig()
        self.azure_search = AzureSearchConfig()
        self.app = AppConfig()
    
    def validate(self) -> bool:
        """Validate all required configurations are present"""
        try:
            # Test Azure OpenAI config
            assert self.azure_openai.endpoint
            assert self.azure_openai.api_key
            assert self.azure_openai.deployment_name
            assert self.azure_openai.embedding_deployment_name
            
            # Test Azure Search config
            assert self.azure_search.endpoint
            assert self.azure_search.api_key
            assert self.azure_search.index_name
            
            # Test app config
            assert self.app.database_path
            assert len(self.app.rss_sources) > 0
            
            return True
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False

# Global config instance
config = Config()

# Validate configuration on import
if not config.validate():
    raise RuntimeError("Invalid configuration. Please check your .env file.")
```

## Key Features to Implement

### 1. Environment Variable Loading
- Use `python-dotenv` to load from `.env` file
- Support both `.env` file and system environment variables
- Environment variables take precedence over `.env` file

### 2. Configuration Validation
- Validate all required Azure credentials are present
- Check that endpoints are properly formatted URLs
- Ensure database path is accessible
- Validate RSS sources are valid URLs

### 3. Type Safety
- Use Pydantic `BaseSettings` for automatic type conversion
- Define proper field types (str, int, list)
- Add field validation where appropriate

### 4. Default Values
- Provide sensible defaults for non-critical settings
- Use environment-specific defaults (local vs Azure)
- Make the system work out-of-the-box for development

### 5. Error Handling
- Clear error messages for missing required variables
- Graceful fallbacks for optional settings
- Validation that fails fast with helpful messages

## Configuration Structure

### Azure OpenAI Settings
- `AZURE_OPENAI_ENDPOINT`: Full endpoint URL
- `AZURE_OPENAI_API_KEY`: API key for authentication
- `AZURE_OPENAI_API_VERSION`: API version (default: 2024-02-15-preview)
- `AZURE_OPENAI_DEPLOYMENT_NAME`: GPT-4o deployment name
- `AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME`: text-embedding-3-large deployment name

### Azure AI Search Settings
- `AZURE_SEARCH_ENDPOINT`: Search service endpoint
- `AZURE_SEARCH_API_KEY`: Search service API key
- `AZURE_SEARCH_INDEX_NAME`: Index name for vector storage

### Application Settings
- `DATABASE_PATH`: SQLite database file path
- `TOP_N_MORNING_BRIEF`: Number of articles in morning brief (default: 10)
- `DEFAULT_TIMEFRAME_DAYS`: Default search timeframe (default: 30)
- `LOG_LEVEL`: Logging level (default: INFO)
- `RSS_SOURCES`: Comma-separated list of RSS feed URLs

## Testing the Configuration

Create a simple test script to verify configuration loading:

```python
# test_config.py
from backend.config import config

def test_config():
    print("Azure OpenAI Endpoint:", config.azure_openai.endpoint)
    print("Database Path:", config.app.database_path)
    print("RSS Sources:", config.app.rss_sources)
    print("Configuration valid:", config.validate())

if __name__ == "__main__":
    test_config()
```

## Validation Checklist
- [ ] All required environment variables are defined
- [ ] Configuration validation works correctly
- [ ] Default values are sensible for development
- [ ] Error messages are clear and helpful
- [ ] Type conversion works for all field types
- [ ] RSS sources can be parsed from comma-separated string
- [ ] Configuration can be imported without errors

## Next Steps
After completing this todo, proceed to "03-backend-models" to define the data models and database schema.
