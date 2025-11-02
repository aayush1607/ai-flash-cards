import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, SearchField,
    VectorSearch, HnswAlgorithmConfiguration, VectorSearchProfile
)
from azure.search.documents.models import VectorizedQuery
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
            # Check if index exists and verify it has required fields
            existing_index = self.index_client.get_index(self.index_name)
            
            # Check if index has new required fields (tl_dr, why_it_matters, references, embedding)
            field_names = {field.name for field in existing_index.fields}
            required_fields = {'tl_dr', 'why_it_matters', 'references', 'embedding'}
            missing_fields = required_fields - field_names
            
            # Also check if vector_search is configured
            has_vector_search = (
                existing_index.vector_search is not None and
                len(existing_index.vector_search.profiles) > 0
            )
            
            if missing_fields or not has_vector_search:
                if missing_fields:
                    print(f"Index {self.index_name} exists but is missing fields: {missing_fields}")
                if not has_vector_search:
                    print(f"Index {self.index_name} exists but is missing vector search configuration")
                print("Azure Search doesn't support schema updates. The index needs to be recreated.")
                print("To fix: Run vector_store.recreate_index_with_schema() or delete and recreate manually")
                return
            
            print(f"Index {self.index_name} already exists with correct schema and HNSW vector search")
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
    
    def recreate_index_with_schema(self) -> bool:
        """Delete existing index and recreate it with the updated schema.
        WARNING: This will delete all documents in the index!"""
        try:
            print(f"Recreating index {self.index_name} with updated schema...")
            print("[WARNING] This will delete all existing documents!")
            
            # Check if index exists
            try:
                self.index_client.get_index(self.index_name)
                # Index exists, delete it
                print(f"Deleting existing index {self.index_name}...")
                self.delete_index()
                # Wait a moment for deletion to propagate
                import time
                time.sleep(2)
            except Exception:
                # Index doesn't exist, that's fine
                print(f"Index {self.index_name} doesn't exist, will create new one")
            
            # Create new index with updated schema
            print(f"Creating new index {self.index_name} with updated schema...")
            self._create_index()
            
            print(f"[SUCCESS] Index {self.index_name} recreated successfully")
            print("Next step: Run reindex_vector_store.py to populate it with documents")
            return True
            
        except Exception as e:
            print(f"Error recreating index: {e}")
            import traceback
            traceback.print_exc()
            return False

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
                SearchableField(name="tl_dr", type=SearchFieldDataType.String),
                SearchableField(name="why_it_matters", type=SearchFieldDataType.String),
                SimpleField(name="source", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="published_at", type=SearchFieldDataType.DateTimeOffset, filterable=True, sortable=True),
                SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SimpleField(name="badges", type=SearchFieldDataType.Collection(SearchFieldDataType.String), filterable=True),
                SimpleField(name="references", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),  # Store as array of JSON strings
                SearchableField(name="snippet", type=SearchFieldDataType.String),
                # Vector field for embeddings (3072 dimensions for text-embedding-3-large default)
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=3072,
                    vector_search_profile_name="vector-profile",
                    searchable=True
                )
            ],
            # Configure HNSW vector search algorithm
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="hnsw-config",
                        kind="hnsw",
                        parameters=None  # Use default HNSW parameters
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="vector-profile",
                        algorithm_configuration_name="hnsw-config"
                    )
                ]
            )
        )
        
        self.index_client.create_index(index)
        print(f"Index {self.index_name} created successfully with HNSW vector search")
    
    def upsert_documents(self, cards: List[Card], embeddings: List[List[float]] = None) -> bool:
        """Upsert documents to the search index (replaces existing documents with same ID)"""
        try:
            if not cards:
                print("No cards to upsert")
                return True
            
            documents = []
            for idx, card in enumerate(cards):
                # Create a consistent document ID based on content_id
                # Use content_id directly as ID, but sanitize it
                safe_id = card.content_id.replace(" ", "_").replace(":", "_").replace("/", "_")
                # Convert references to list of JSON strings for storage
                references_json = []
                if card.references:
                    for ref in card.references:
                        # Store reference as JSON string
                        ref_dict = {
                            "label": ref.label,
                            "url": ref.url
                        }
                        references_json.append(json.dumps(ref_dict))
                
                # Get embedding for this card (if provided)
                embedding_value = None
                if embeddings and idx < len(embeddings):
                    embedding_value = embeddings[idx]
                elif embeddings and len(embeddings) == 1:
                    # If only one embedding provided, use it for all cards
                    embedding_value = embeddings[0]
                
                doc = {
                    "id": safe_id,
                    "content_id": card.content_id,
                    "title": card.title or "",
                    "summary": card.summary or "",
                    "tl_dr": card.tl_dr or "",
                    "why_it_matters": card.why_it_matters or "",
                    "source": card.source or "",
                    "type": card.type or "blog",
                    "published_at": card.published_at.isoformat() + "Z",
                    "tags": card.tags or [],
                    "badges": card.badges or [],
                    "references": references_json,
                    "snippet": card.snippet or ""
                }
                
                # Add embedding if available
                if embedding_value:
                    doc["embedding"] = embedding_value
                
                documents.append(doc)
            
            print(f"Upserting {len(documents)} documents to vector store (will replace existing documents with same ID)...")
            
            # upload_documents actually does upsert (replace if exists, insert if new)
            # This replaces any existing document with the same ID
            result = self.search_client.upload_documents(documents)
            
            # Check for errors
            failed_docs = [doc for doc in result if not doc.succeeded]
            if failed_docs:
                print(f"[WARNING] Failed to upload {len(failed_docs)} documents")
                for failed in failed_docs[:5]:  # Show first 5 failures
                    print(f"  - Failed document: {failed}")
                return False
            
            successful_count = len(documents) - len(failed_docs)
            print(f"[SUCCESS] Successfully upserted {successful_count} documents to vector store")
            return True
            
        except Exception as e:
            print(f"Error upserting documents: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cleanup_stale_documents(self, valid_content_ids: List[str]) -> int:
        """Remove documents from vector store that don't exist in the valid content_ids list"""
        try:
            print(f"Checking for stale documents in vector store (keeping {len(valid_content_ids)} valid IDs)...")
            
            # Get all documents from vector store
            all_results = self.search_client.search(search_text="*", top=10000, select=["id", "content_id"])
            
            valid_ids_set = {cid.replace(" ", "_").replace(":", "_").replace("/", "_") for cid in valid_content_ids}
            
            stale_doc_ids = []
            total_docs = 0
            
            for result in all_results:
                total_docs += 1
                doc_id = result.get("id")
                content_id = result.get("content_id", "")
                
                # Check if this document's content_id is in our valid list
                # Compare both the stored content_id and the ID format
                is_valid = (
                    content_id in valid_content_ids or 
                    doc_id in valid_ids_set
                )
                
                if not is_valid:
                    stale_doc_ids.append({"id": doc_id})
            
            if stale_doc_ids:
                print(f"Found {len(stale_doc_ids)} stale documents out of {total_docs} total, removing...")
                delete_result = self.search_client.delete_documents(documents=stale_doc_ids)
                failed_deletes = [doc for doc in delete_result if not doc.succeeded]
                if failed_deletes:
                    print(f"[WARNING] Failed to delete {len(failed_deletes)} stale documents")
                else:
                    print(f"[SUCCESS] Successfully removed {len(stale_doc_ids)} stale documents")
                return len(stale_doc_ids) - len(failed_deletes)
            else:
                print(f"[SUCCESS] No stale documents found ({total_docs} total documents, all valid)")
                return 0
                
        except Exception as e:
            print(f"Error cleaning up stale documents: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def semantic_search(self, query: str, top_k: int = 15, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Perform semantic search using HNSW vector search with optional date filtering"""
        try:            
            # Build filter expression
            filter_expr = None
            if days:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                filter_expr = f"published_at ge {cutoff_date.isoformat()}Z"
            
            # Generate embedding for the query using HNSW vector search
            query_embedding = self._get_query_embedding(query)
            
            print(f"Vector search (HNSW): query='{query}', filter={filter_expr}, top_k={top_k}, embedding_dim={len(query_embedding)}")
            
            # Create vector query for HNSW search
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k,
                fields="embedding"
            )
            
            # Perform pure vector search using HNSW algorithm
            # HNSW provides efficient approximate nearest neighbor search for semantic similarity
            results = self.search_client.search(
                search_text="*",  # Empty query - we're only using vector search
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k,
                include_total_count=True
            )
            
            # Convert results to list of dictionaries
            search_results = []
            result_count = 0
            for result in results:
                result_count += 1
                # Parse references from JSON strings back to dictionaries
                references_list = []
                refs_data = result.get("references", [])
                if refs_data:
                    for ref_str in refs_data:
                        try:
                            ref_dict = json.loads(ref_str)
                            references_list.append(ref_dict)
                        except (json.JSONDecodeError, TypeError):
                            # If it's already a dict, use it directly
                            if isinstance(ref_str, dict):
                                references_list.append(ref_str)
                
                search_results.append({
                    "content_id": result.get("content_id", ""),
                    "title": result.get("title", ""),
                    "summary": result.get("summary", ""),
                    "tl_dr": result.get("tl_dr", ""),
                    "why_it_matters": result.get("why_it_matters", ""),
                    "source": result.get("source", ""),
                    "type": result.get("type", ""),
                    "published_at": result.get("published_at", ""),
                    "tags": result.get("tags", []),
                    "badges": result.get("badges", []),
                    "references": references_list,
                    "snippet": result.get("snippet", ""),
                    "score": result.get("@search.score", 0.0)
                })
            
            print(f"Vector search (HNSW): returned {result_count} results (search_results list has {len(search_results)} items)")
            
            return search_results[:top_k]  # Ensure we don't exceed top_k
            
        except Exception as e:
            print(f"Error performing semantic search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for search query"""
        from backend.summarizer import summarizer
        return summarizer.embed_text(query)
    
    def reindex_all_summarized_articles(self) -> Dict[str, Any]:
        """Re-index all summarized articles from database to vector store"""
        try:
            from backend.database import db_manager
            from backend.summarizer import summarizer
            
            print("Re-indexing all summarized articles from database to vector store...")
            
            # Get all summarized articles from database
            with db_manager.get_session() as session:
                from backend.models import Article
                articles = session.query(Article).filter(
                    Article.is_summarized == True
                ).all()
            
            if not articles:
                # Provide diagnostic information
                with db_manager.get_session() as session:
                    total_articles = session.query(Article).count()
                    summarized_count = session.query(Article).filter(Article.is_summarized == True).count()
                    relevance_checked = session.query(Article).filter(Article.is_relevance_check_done == True).count()
                    relevant = session.query(Article).filter(Article.is_relevant == True).count()
                
                diagnostic_msg = (
                    f"No summarized articles found. "
                    f"Total articles: {total_articles}, "
                    f"Summarized: {summarized_count}, "
                    f"Relevance checked: {relevance_checked}, "
                    f"Relevant: {relevant}"
                )
                print(diagnostic_msg)
                return {
                    'success': True, 
                    'indexed': 0, 
                    'message': 'No articles to index',
                    'diagnostics': {
                        'total_articles': total_articles,
                        'summarized': summarized_count,
                        'relevance_checked': relevance_checked,
                        'relevant': relevant
                    }
                }
            
            print(f"Found {len(articles)} summarized articles, converting to cards and indexing...")
            
            # Convert articles to cards
            cards = []
            embeddings = []
            indexed_count = 0
            failed_count = 0
            
            for article in articles:
                try:
                    # Convert Article to Card using to_card() method
                    card = article.to_card()
                    if not card:
                        print(f"Skipping article {article.content_id} - to_card() returned None")
                        failed_count += 1
                        continue
                    
                    cards.append(card)
                    
                    # Generate embedding
                    embedding = summarizer.embed_text(f"{card.title} {card.tl_dr} {card.summary} {card.why_it_matters}")
                    embeddings.append(embedding)
                    indexed_count += 1
                    
                except Exception as e:
                    print(f"Error processing article {article.content_id}: {e}")
                    failed_count += 1
                    continue
            
            # Index all cards to vector store
            if cards and embeddings:
                print(f"Upserting {len(cards)} articles to vector store...")
                success = self.upsert_documents(cards, embeddings)
                
                if success:
                    print(f"[SUCCESS] Successfully re-indexed {indexed_count} articles")
                    return {
                        'success': True,
                        'indexed': indexed_count,
                        'failed': failed_count,
                        'message': f'Re-indexed {indexed_count} articles, {failed_count} failed'
                    }
                else:
                    print(f"[WARNING] Failed to index articles to vector store")
                    return {
                        'success': False,
                        'indexed': 0,
                        'failed': failed_count,
                        'message': 'Failed to upload documents to vector store'
                    }
            else:
                print(f"No cards to index (processed {indexed_count}, failed {failed_count})")
                return {
                    'success': False,
                    'indexed': indexed_count,
                    'failed': failed_count,
                    'message': f'No cards generated - {failed_count} failed'
                }
                
        except Exception as e:
            print(f"Error re-indexing articles: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'indexed': 0,
                'failed': 0,
                'message': f'Error: {str(e)}'
            }
    
    def get_document_count(self) -> int:
        """Get total number of documents in the index"""
        try:
            results = self.search_client.search(
                search_text="*",
                top=1,
                include_total_count=True
            )
            # The results iterator has a get_count() method or we can check the first result
            for result in results:
                # Just accessing results populates the count
                pass
            # Try to get count from response - this may vary by SDK version
            # For now, do a quick count search
            count_results = self.search_client.search(search_text="*", top=1000)
            count = sum(1 for _ in count_results)
            return count
        except Exception as e:
            print(f"Error getting document count: {e}")
            return 0

# Global vector store manager
vector_store = VectorStoreManager()
