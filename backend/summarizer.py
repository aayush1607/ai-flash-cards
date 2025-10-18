import json
from typing import List, Tuple, Optional, Dict, Any
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
