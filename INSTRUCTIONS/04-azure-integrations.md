# Todo 4: Azure AI Search and Azure OpenAI Integrations

## Objective
Implement Azure AI Search for vector storage and semantic search, and Azure OpenAI for content summarization and embedding generation.

## Files to Create

### 1. `backend/vector_store.py`
Create Azure AI Search integration:

```python
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, 
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile,
    SemanticSearch, SemanticConfiguration, SemanticPrioritizedFields,
    SemanticField, SemanticSearchFieldType
)
from azure.core.credentials import AzureKeyCredential
from backend.config import config
from backend.models import Card

class VectorStoreManager:
    """Azure AI Search vector store manager"""
    
    def __init__(self):
        self.endpoint = config.azure_search.endpoint
        self.api_key = config.azure_search.api_key
        self.index_name = config.azure_search.index_name
        
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
    
    def _create_index(self):
        """Create the search index with vector and semantic search capabilities"""
        index = SearchIndex(
            name=self.index_name,
            fields=[
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="content_id", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="title", type=SearchFieldDataType.String, searchable=True),
                SimpleField(name="summary", type=SearchFieldDataType.String, searchable=True),
                SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="published_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SimpleField(name="badges", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SimpleField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), vector_search_dimensions=1536),
                SimpleField(name="snippet", type=SearchFieldDataType.String, searchable=True)
            ],
            vector_search=VectorSearch(
                algorithms=[HnswAlgorithmConfiguration(name="hnsw-config")],
                profiles=[VectorSearchProfile(name="vector-profile", algorithm="hnsw-config")]
            ),
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="semantic-config",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=SemanticField(field_name="title"),
                            content_fields=[
                                SemanticField(field_name="summary"),
                                SemanticField(field_name="snippet")
                            ],
                            keywords_fields=[
                                SemanticField(field_name="tags"),
                                SemanticField(field_name="badges")
                            ]
                        )
                    )
                ]
            )
        )
        
        self.index_client.create_index(index)
        print(f"Index {self.index_name} created successfully")
    
    def upsert_documents(self, cards: List[Card], embeddings: List[List[float]]) -> bool:
        """Upsert documents with embeddings to the search index"""
        try:
            documents = []
            for card, embedding in zip(cards, embeddings):
                doc = {
                    "id": card.content_id,
                    "content_id": card.content_id,
                    "title": card.title,
                    "summary": card.summary,
                    "source": card.source,
                    "type": card.type,
                    "published_at": card.published_at.isoformat(),
                    "tags": card.tags,
                    "badges": card.badges,
                    "embedding": embedding,
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
                filter_expr = f"published_at ge {cutoff_date.isoformat()}"
            
            # Perform hybrid search (vector + semantic)
            results = self.search_client.search(
                search_text=query,
                vector_queries=[
                    {
                        "vector": self._get_query_embedding(query),
                        "k_nearest_neighbors": top_k,
                        "fields": "embedding"
                    }
                ],
                filter=filter_expr,
                top=top_k,
                include_total_count=True,
                semantic_configuration_name="semantic-config"
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
        """Get embedding for search query (placeholder - will be implemented in summarizer.py)"""
        # This will be implemented in summarizer.py
        from backend.summarizer import embed_text
        return embed_text(query)

# Global vector store manager
vector_store = VectorStoreManager()
```

### 2. `backend/summarizer.py`
Create Azure OpenAI integration:

```python
import json
from typing import List, Tuple, Optional, Dict, Any
from openai import AzureOpenAI
from backend.config import config
from backend.models import Card, Reference

class Summarizer:
    """Azure OpenAI summarization and embedding service"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=config.azure_openai.endpoint,
            api_key=config.azure_openai.api_key,
            api_version=config.azure_openai.api_version
        )
        self.deployment_name = config.azure_openai.deployment_name
        self.embedding_deployment_name = config.azure_openai.embedding_deployment_name
    
    def summarize_content(self, title: str, raw_text: str, source: str, url: str) -> Tuple[str, str, str, List[str], List[Reference]]:
        """Summarize content and extract metadata"""
        try:
            # Prepare content for summarization
            content = f"Title: {title}\n\nContent: {raw_text[:4000]}"  # Limit content length
            
            # Create summarization prompt
            prompt = f"""
You are an AI research analyst. Analyze this AI research/news content and provide:

1. TL;DR: One sentence summary (≤140 characters) - the key insight
2. Summary: 2-3 concise, factual sentences explaining what this is about
3. Why it matters: One short sentence explaining the significance/impact
4. Tags: 1-3 topical tags (e.g., "transformer", "computer-vision", "efficiency")
5. References: Extract any relevant links (papers, code, datasets) from the content

Content:
{content}

Respond in JSON format:
{{
    "tl_dr": "One sentence summary...",
    "summary": "2-3 sentence explanation...",
    "why_it_matters": "Why this is significant...",
    "tags": ["tag1", "tag2", "tag3"],
    "references": [
        {{"label": "Paper", "url": "https://..."}},
        {{"label": "Code", "url": "https://..."}}
    ]
}}
"""
            
            # Call Azure OpenAI
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert AI research analyst. Provide accurate, concise summaries in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            
            # Validate and clean results
            tl_dr = result.get("tl_dr", title[:140])
            if len(tl_dr) > 140:
                tl_dr = tl_dr[:137] + "..."
            
            summary = result.get("summary", "Content summary not available.")
            why_it_matters = result.get("why_it_matters", "Research significance not determined.")
            tags = result.get("tags", [])[:3]  # Limit to 3 tags
            
            # Process references
            references = []
            for ref in result.get("references", []):
                if isinstance(ref, dict) and "url" in ref:
                    references.append(Reference(
                        label=ref.get("label", "Reference"),
                        url=ref["url"]
                    ))
            
            # Add source reference if no others found
            if not references and url:
                references.append(Reference(label="Source", url=url))
            
            return tl_dr, summary, why_it_matters, tags, references
            
        except Exception as e:
            print(f"Error summarizing content: {e}")
            # Fallback to basic extraction
            return self._fallback_summarization(title, raw_text, url)
    
    def _fallback_summarization(self, title: str, raw_text: str, url: str) -> Tuple[str, str, str, List[str], List[Reference]]:
        """Fallback summarization when AI fails"""
        # Use title as TL;DR
        tl_dr = title[:140] if len(title) <= 140 else title[:137] + "..."
        
        # Basic summary from first few sentences
        sentences = raw_text.split('.')[:2]
        summary = '. '.join(sentences).strip()
        if not summary:
            summary = "Content summary not available."
        
        why_it_matters = "Research significance not determined."
        tags = []
        
        # Basic reference
        references = []
        if url:
            references.append(Reference(label="Source", url=url))
        
        return tl_dr, summary, why_it_matters, tags, references
    
    def generate_topic_summary(self, topic: str, retrieved_docs: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Generate topic summary from retrieved documents"""
        try:
            # Prepare context from retrieved documents
            context = f"Topic: {topic}\n\nRetrieved documents:\n"
            for i, doc in enumerate(retrieved_docs[:5]):  # Use top 5 docs
                context += f"{i+1}. {doc['title']}\n{doc['summary']}\n\n"
            
            prompt = f"""
You are an AI research analyst. Based on the retrieved documents about "{topic}", provide:

1. Topic Summary: 2-3 sentences synthesizing the key trends and developments
2. Why it matters: One sentence explaining the significance of this topic

Context:
{context}

Respond in JSON format:
{{
    "topic_summary": "2-3 sentence synthesis...",
    "why_it_matters": "Why this topic is significant..."
}}
"""
            
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an expert AI research analyst. Provide accurate, concise topic summaries in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            result = json.loads(response.choices[0].message.content)
            
            topic_summary = result.get("topic_summary", f"Recent developments in {topic}.")
            why_it_matters = result.get("why_it_matters", "This topic is significant for AI research.")
            
            return topic_summary, why_it_matters
            
        except Exception as e:
            print(f"Error generating topic summary: {e}")
            return f"Recent developments in {topic}.", "This topic is significant for AI research."
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_deployment_name,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536
    
    def extract_badges(self, content: str, references: List[Reference]) -> List[str]:
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
        
        # Check for benchmarks
        if any(word in content_lower for word in ['benchmark', 'evaluation', 'performance']):
            badges.append('BENCHMARK')
        
        return badges

# Global summarizer instance
summarizer = Summarizer()
```

## Key Features to Implement

### 1. Azure AI Search Integration
- **Index Management**: Create index with vector and semantic search capabilities
- **Document Upsert**: Upload documents with embeddings
- **Semantic Search**: Hybrid search combining vector similarity and semantic understanding
- **Date Filtering**: Support for time-based search queries
- **Error Handling**: Graceful fallbacks for search failures

### 2. Azure OpenAI Integration
- **Content Summarization**: Generate TL;DR, summary, and significance
- **Topic Synthesis**: Create topic summaries from multiple documents
- **Embedding Generation**: Create vector embeddings for semantic search
- **Badge Extraction**: Analyze content for relevant badges
- **Fallback Handling**: Basic summarization when AI fails

### 3. Vector Search Capabilities
- **Hybrid Search**: Combine vector similarity with semantic search
- **Semantic Understanding**: Use semantic search for better relevance
- **Filtering**: Support for date, type, and other filters
- **Scoring**: Return relevance scores for ranking

### 4. Content Processing
- **Structured Output**: JSON-formatted responses from AI
- **Validation**: Ensure output meets requirements
- **Reference Extraction**: Identify and extract relevant links
- **Tag Generation**: Create topical tags for content

## Azure AI Search Index Schema

### Fields
- **id**: Unique identifier (content_id)
- **content_id**: Content identifier for filtering
- **title**: Searchable title field
- **summary**: Searchable summary field
- **source**: Filterable source field
- **type**: Filterable content type
- **published_at**: Sortable and filterable date
- **tags**: Filterable tag collection
- **badges**: Filterable badge collection
- **embedding**: Vector field (1536 dimensions)
- **snippet**: Searchable snippet field

### Vector Search Configuration
- **Algorithm**: HNSW for efficient vector search
- **Dimensions**: 1536 (text-embedding-3-large)
- **Profile**: Vector search profile for queries

### Semantic Search Configuration
- **Title Field**: Prioritized title field
- **Content Fields**: Summary and snippet fields
- **Keywords Fields**: Tags and badges fields

## Validation Checklist
- [ ] Azure AI Search index is created with proper schema
- [ ] Vector search works with embeddings
- [ ] Semantic search provides relevant results
- [ ] Date filtering works correctly
- [ ] Document upsert handles errors gracefully
- [ ] Azure OpenAI summarization produces valid JSON
- [ ] Embedding generation works for search queries
- [ ] Topic summarization synthesizes multiple documents
- [ ] Badge extraction identifies relevant badges
- [ ] Fallback mechanisms work when AI fails

## Next Steps
After completing this todo, proceed to "05-ingestion-pipeline" to implement the RSS crawling and content processing pipeline.
