import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class that reads from environment variables"""
    
    def __init__(self):
        # Azure OpenAI Configuration
        self.azure_openai_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        self.azure_openai_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        self.azure_openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
        self.azure_openai_deployment_name = os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME', 'gpt-4')
        self.azure_openai_embedding_deployment_name = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME', 'text-embedding-3-large')
        
        # Azure AI Search Configuration
        self.azure_search_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT')
        self.azure_search_api_key = os.getenv('AZURE_SEARCH_API_KEY')
        self.azure_search_index_name = os.getenv('AZURE_SEARCH_INDEX_NAME', 'aiflash-index')
        
        # Application Settings
        self.database_path = os.getenv('DATABASE_PATH', os.path.join('data', 'aiflash.db'))
        # Ensure we use an absolute path to avoid working directory issues
        if not os.path.isabs(self.database_path):
            # Get the directory where this config file is located
            config_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level to the project root
            project_root = os.path.dirname(config_dir)
            self.database_path = os.path.join(project_root, self.database_path)
        self.morning_brief_top_n = int(os.getenv('TOP_N_MORNING_BRIEF', '10'))
        self.topic_feed_top_k = 15
        self.allowed_origins = ["*"]  # For CORS
        
        # Validate required settings
        self._validate()
    
    def _validate(self):
        """Validate that all required configuration is present"""
        required_vars = [
            ('AZURE_OPENAI_ENDPOINT', self.azure_openai_endpoint),
            ('AZURE_OPENAI_API_KEY', self.azure_openai_api_key),
            ('AZURE_OPENAI_DEPLOYMENT_NAME', self.azure_openai_deployment_name),
            ('AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME', self.azure_openai_embedding_deployment_name),
            ('AZURE_SEARCH_ENDPOINT', self.azure_search_endpoint),
            ('AZURE_SEARCH_API_KEY', self.azure_search_api_key),
        ]
        
        missing = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing.append(var_name)
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

# Global config instance
config = Config()