import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, 
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile
)
from azure.core.credentials import AzureKeyCredential
from backend.config import config
from backend.models import Card

class VectorStoreManager:
    """Azure AI Search vector store manager"""
    
    def __init__(self):
        self.endpoint = config.azure_search_endpoint
        self.api_key = config.azure_search_api_key
        self.index_name = config.azure_search_index_name
        
        # Initialize clients
        self.credential = AzureKeyCredential(self.api_key)
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential
        )
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential
        )
        
        # Ensure index exists
        self._ensure_index_exists()
    
    def _ensure_index_exists(self):
        """Create search index if it doesn't exist"""
        try:
            # Check if index exists
            self.index_client.get_index(self.index_name)
            print(f"Index {self.index_name} already exists")
        except Exception:
            # Create index
            print(f"Creating index {self.index_name}")
            self._create_index()
    
    def delete_index(self):
        """Delete the search index"""
        try:
            self.index_client.delete_index(self.index_name)
            print(f"Index {self.index_name} deleted successfully")
        except Exception as e:
            print(f"Error deleting index {self.index_name}: {e}")

    def clear_all_documents(self) -> bool:
        """Clear all documents from the search index"""
        try:
            # Get all documents to delete them
            results = self.search_client.search(search_text="*", top=10000)  # Get all documents
            
            if not results:
                print("No documents to clear from vector index")
                return True
            
            # Extract document IDs
            doc_ids = []
            for result in results:
                doc_ids.append({"id": result["id"]})
            
            if doc_ids:
                # Delete all documents
                delete_result = self.search_client.delete_documents(documents=doc_ids)
                
                # Check for errors
                failed_docs = [doc for doc in delete_result if not doc.succeeded]
                if failed_docs:
                    print(f"Failed to delete {len(failed_docs)} documents from vector index")
                    return False
                
                print(f"Cleared {len(doc_ids)} documents from vector index")
                return True
            else:
                print("No documents found in vector index")
                return True
                
        except Exception as e:
            print(f"Error clearing documents from vector index: {e}")
            return False

    def _create_index(self):
        """Create the search index with vector and semantic search capabilities"""
        
        from azure.search.documents.indexes.models import SearchableField
        
        index = SearchIndex(
            name=self.index_name,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="content_id", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="title", type=SearchFieldDataType.String),
                SearchableField(name="summary", type=SearchFieldDataType.String),
                SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="published_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SimpleField(name="badges", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SearchableField(name="snippet", type=SearchFieldDataType.String)
            ]
        )
        
        self.index_client.create_index(index)
        print(f"Index {self.index_name} created successfully")
    
    def upsert_documents(self, cards: List[Card], embeddings: List[List[float]] = None) -> bool:
        """Upsert documents to the search index (without embeddings for now)"""
        try:
            documents = []
            for card in cards:
                # Create a safe document ID (replace spaces and colons with underscores)
                safe_id = card.content_id.replace(" ", "_").replace(":", "_")
                doc = {
                    "id": safe_id,
                    "content_id": card.content_id,
                    "title": card.title,
                    "summary": card.summary,
                    "source": card.source,
                    "type": card.type,
                    "published_at": card.published_at.isoformat() + "Z",
                    "tags": card.tags,
                    "badges": card.badges,
                    "snippet": card.snippet or ""
                }
                documents.append(doc)
            
            # Upsert documents
            result = self.search_client.upload_documents(documents)
            
            # Check for errors
            failed_docs = [doc for doc in result if not doc.succeeded]
            if failed_docs:
                print(f"Failed to upload {len(failed_docs)} documents")
                return False
            
            print(f"Successfully uploaded {len(documents)} documents")
            return True
            
        except Exception as e:
            print(f"Error upserting documents: {e}")
            return False
    
    def semantic_search(self, query: str, top_k: int = 15, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Perform semantic search with optional date filtering"""
        try:
            # Build filter expression
            filter_expr = None
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                filter_expr = f"published_at ge {cutoff_date.isoformat()}Z"
            
            # Perform text search for now
            results = self.search_client.search(
                search_text=query,
                filter=filter_expr,
                top=top_k,
                include_total_count=True
            )
            
            # Convert results to list of dictionaries
            search_results = []
            for result in results:
                search_results.append({
                    "content_id": result["content_id"],
                    "title": result["title"],
                    "summary": result["summary"],
                    "source": result["source"],
                    "type": result["type"],
                    "published_at": result["published_at"],
                    "tags": result.get("tags", []),
                    "badges": result.get("badges", []),
                    "snippet": result.get("snippet", ""),
                    "score": result.get("@search.score", 0.0)
                })
            
            return search_results
            
        except Exception as e:
            print(f"Error performing semantic search: {e}")
            return []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for search query"""
        from backend.summarizer import summarizer
        return summarizer.embed_text(query)

# Global vector store manager
vector_store = VectorStoreManager()
