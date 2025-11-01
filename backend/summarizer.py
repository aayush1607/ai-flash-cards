import json
import re
from typing import List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse
from openai import AzureOpenAI
from backend.config import config
from backend.models import Card, Reference

class Summarizer:
    """Azure OpenAI summarization and embedding service"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            azure_endpoint=config.azure_openai_endpoint,
            api_key=config.azure_openai_api_key,
            api_version=config.azure_openai_api_version
        )
        self.deployment_name = config.azure_openai_deployment_name
        self.embedding_deployment_name = config.azure_openai_embedding_deployment_name
    
    def _normalize_url(self, url: str) -> str:
        """Normalize URL for comparison (removes trailing slashes, converts to lowercase, etc.)"""
        if not url:
            return ""
        
        url = url.strip()
        
        # Parse URL
        try:
            parsed = urlparse(url)
            
            # Normalize scheme to lowercase
            scheme = parsed.scheme.lower()
            
            # Normalize netloc to lowercase and remove www. prefix for comparison
            netloc = parsed.netloc.lower()
            if netloc.startswith('www.'):
                netloc = netloc[4:]
            
            # Normalize path (remove trailing slash, lowercase)
            path = parsed.path.rstrip('/').lower()
            
            # Normalize query (sort parameters for consistency)
            query = parsed.query
            if query:
                # Sort query parameters
                params = sorted(query.split('&'))
                query = '&'.join(params)
            
            # Reconstruct normalized URL
            normalized = f"{scheme}://{netloc}{path}"
            if query:
                normalized += f"?{query}"
            if parsed.fragment:
                normalized += f"#{parsed.fragment.lower()}"
            
            return normalized
        except Exception:
            # If parsing fails, just normalize basic things
            return url.lower().rstrip('/')
    
    def _urls_are_similar(self, url1: str, url2: str) -> bool:
        """Check if two URLs are essentially the same (handles variations)"""
        if not url1 or not url2:
            return False
        
        # Normalize both URLs
        norm1 = self._normalize_url(url1)
        norm2 = self._normalize_url(url2)
        
        # Exact match after normalization
        if norm1 == norm2:
            return True
        
        # Check if one is a prefix of the other (handles trailing slash differences)
        # e.g., "https://example.com" vs "https://example.com/"
        if norm1.rstrip('/') == norm2.rstrip('/'):
            return True
        
        # Check domain similarity (handle www vs non-www)
        try:
            parsed1 = urlparse(url1)
            parsed2 = urlparse(url2)
            
            netloc1 = parsed1.netloc.lower().lstrip('www.')
            netloc2 = parsed2.netloc.lower().lstrip('www.')
            
            # If domains match and paths are very similar
            if netloc1 == netloc2:
                path1 = parsed1.path.lower().rstrip('/')
                path2 = parsed2.path.lower().rstrip('/')
                
                # Exact path match (after normalization)
                if path1 == path2:
                    return True
                
                # One path is empty and other is just "/"
                if (path1 == '' and path2 == '/') or (path1 == '/' and path2 == ''):
                    return True
        except Exception:
            pass
        
        return False
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate if URL is valid and not a placeholder"""
        if not url or not isinstance(url, str):
            return False
        
        url = url.strip()
        
        # Check for placeholder patterns
        placeholder_patterns = [
            r'link_to_',
            r'placeholder',
            r'example\.com',
            r'\.\.\.',
            r'https?://link',
            r'https?://url',
            r'https?://www\.example',
            r'REPLACE',
            r'YOUR_'
        ]
        
        for pattern in placeholder_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # Must start with http:// or https://
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Parse URL to check if it's well-formed
        try:
            parsed = urlparse(url)
            # Must have a valid netloc (domain)
            if not parsed.netloc:
                return False
            # Must not have invalid characters
            if ' ' in url:
                return False
            return True
        except Exception:
            return False
    
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
5. References: Extract ONLY real, actual URLs from the content (papers, code repositories, datasets, documentation)

IMPORTANT for References:
- ONLY include URLs that actually appear in the content text
- Extract full, complete URLs (e.g., "https://arxiv.org/abs/2023.12345" or "https://github.com/user/repo")
- DO NOT create placeholder URLs like "https://link_to_..." or "https://example.com/..."
- DO NOT make up or invent URLs that are not in the content
- If you find real URLs in the content, include them with descriptive labels
- If no real URLs are found, return an empty references array []

Source URL: {url}

Content:
{content}

Respond in JSON format:
{{
    "tl_dr": "One sentence summary...",
    "summary": "2-3 sentence explanation...",
    "why_it_matters": "Why this is significant...",
    "tags": ["tag1", "tag2", "tag3"],
    "references": [
        {{"label": "Paper", "url": "https://arxiv.org/abs/..."}},
        {{"label": "GitHub Repository", "url": "https://github.com/..."}}
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
            
            # Process references - validate URLs and filter out invalid ones
            references = []
            for ref in result.get("references", []):
                if isinstance(ref, dict) and "url" in ref:
                    ref_url = ref["url"]
                    # Only add if URL is valid
                    if self._is_valid_url(ref_url):
                        references.append(Reference(
                            label=ref.get("label", "Reference"),
                            url=ref_url
                        ))
                    else:
                        print(f"Skipping invalid reference URL: {ref_url}")
            
            # Always add source URL as a reference (if valid) - ensures at least one valid link
            source_url_valid = url and self._is_valid_url(url)
            if source_url_valid:
                # Check if source URL is already in references (using smart matching)
                source_already_added = any(self._urls_are_similar(ref.url, url) for ref in references)
                if not source_already_added:
                    references.append(Reference(label="Source", url=url))
            elif url:
                print(f"Skipping invalid source URL: {url}")
            
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
        
        # Basic reference (validate URL)
        references = []
        if url and self._is_valid_url(url):
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
            why_it_matters = result.get("why_it_matters", "Significance not determined.")
            
            return topic_summary, why_it_matters
            
        except Exception as e:
            print(f"Error generating topic summary: {e}")
            return f"Recent developments in {topic}.", "Significance not determined."
    
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
