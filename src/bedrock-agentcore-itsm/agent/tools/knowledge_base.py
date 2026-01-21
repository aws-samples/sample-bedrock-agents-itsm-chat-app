"""
KnowledgeBaseTool implementation for ITSM knowledge base queries.

This tool provides knowledge base query functionality that maintains equivalent
functionality to the Bedrock Agents implementation while using the Bedrock
Runtime API for knowledge base integration.
"""

import json
import logging
import os
from typing import Dict, Any, List, Optional

import boto3
from strands import Tool

logger = logging.getLogger(__name__)


class KnowledgeBaseTool(Tool):
    """
    Tool for querying ITSM knowledge base through Bedrock Runtime API.
    
    This tool ensures equivalent functionality to the Bedrock Agents
    knowledge base integration while providing direct control over
    the query process and response formatting.
    """
    
    def __init__(self):
        """Initialize the KnowledgeBaseTool with Bedrock configuration."""
        super().__init__()
        
        self.name = "knowledge_base_query"
        self.description = "Query the ITSM knowledge base for solutions and documentation"
        
        # Bedrock configuration
        self.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', '')
        self.model_id = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')
        
        # Query configuration
        self.max_results = int(os.getenv('KB_MAX_RESULTS', '5'))
        self.confidence_threshold = float(os.getenv('KB_CONFIDENCE_THRESHOLD', '0.7'))
        
        # Initialize Bedrock clients
        self.bedrock_agent_client = boto3.client('bedrock-agent-runtime')
        self.bedrock_runtime_client = boto3.client('bedrock-runtime')
        
        logger.info(f"KnowledgeBaseTool initialized with KB ID: {self.knowledge_base_id}")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute knowledge base query with the provided parameters.
        
        Args:
            parameters: Dictionary containing query parameters:
                - query: The search query or question
                - max_results: Optional maximum number of results (default: 5)
                - include_sources: Optional flag to include source references
        
        Returns:
            Dictionary containing the knowledge base response and sources
        """
        try:
            # Extract and validate query
            query = parameters.get('query', '').strip()
            if not query:
                return {
                    'statusCode': 400,
                    'error': 'Invalid query',
                    'answer': 'Please provide a valid search query or question.'
                }
            
            # Extract optional parameters
            max_results = parameters.get('max_results', self.max_results)
            include_sources = parameters.get('include_sources', True)
            
            # Retrieve relevant documents from knowledge base
            retrieval_results = await self._retrieve_documents(query, max_results)
            
            if not retrieval_results:
                return {
                    'statusCode': 200,
                    'answer': 'I could not find relevant information in the knowledge base for your query.',
                    'sources': [],
                    'confidence': 0.0
                }
            
            # Generate answer using retrieved context
            answer_response = await self._generate_answer(query, retrieval_results)
            
            # Format response
            response = {
                'statusCode': 200,
                'answer': answer_response['answer'],
                'confidence': answer_response['confidence'],
                'query': query
            }
            
            # Include sources if requested
            if include_sources:
                response['sources'] = self._format_sources(retrieval_results)
            
            logger.info(f"Knowledge base query completed successfully for: {query[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Error querying knowledge base: {str(e)}")
            return {
                'statusCode': 500,
                'error': 'Knowledge base query failed',
                'answer': f'I encountered an error while searching the knowledge base: {str(e)}'
            }
    
    async def _retrieve_documents(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents from the knowledge base.
        
        Args:
            query: Search query
            max_results: Maximum number of results to retrieve
            
        Returns:
            List of retrieved document chunks with metadata
        """
        try:
            if not self.knowledge_base_id:
                logger.warning("Knowledge base ID not configured")
                return []
            
            # Call Bedrock Agent Runtime to retrieve documents
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': max_results,
                        'overrideSearchType': 'HYBRID'  # Use both semantic and keyword search
                    }
                }
            )
            
            # Extract and filter results by confidence
            results = []
            for item in response.get('retrievalResults', []):
                confidence = item.get('score', 0.0)
                
                # Only include results above confidence threshold
                if confidence >= self.confidence_threshold:
                    results.append({
                        'content': item.get('content', {}).get('text', ''),
                        'confidence': confidence,
                        'source': item.get('location', {}).get('s3Location', {}).get('uri', ''),
                        'metadata': item.get('metadata', {})
                    })
            
            # Sort by confidence score
            results.sort(key=lambda x: x['confidence'], reverse=True)
            
            logger.info(f"Retrieved {len(results)} relevant documents")
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            return []
    
    async def _generate_answer(self, query: str, retrieval_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an answer using retrieved context and Bedrock model.
        
        Args:
            query: Original user query
            retrieval_results: Retrieved document chunks
            
        Returns:
            Dictionary containing generated answer and confidence
        """
        try:
            # Prepare context from retrieved documents
            context_parts = []
            for i, result in enumerate(retrieval_results[:3]):  # Use top 3 results
                context_parts.append(f"Source {i+1}:\n{result['content']}\n")
            
            context = "\n".join(context_parts)
            
            # Prepare prompt for answer generation
            prompt = f"""You are an IT Service Management assistant. Use the following context from the knowledge base to answer the user's question.

Context:
{context}

User Question: {query}

Instructions:
- Provide a helpful and accurate answer based on the context
- If the context doesn't contain enough information, say so clearly
- Keep your response concise but complete
- Focus on practical solutions and actionable advice
- If referencing specific procedures, mention them clearly

Answer:"""
            
            # Call Bedrock model for answer generation
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "temperature": 0.1,  # Low temperature for factual responses
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_runtime_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            answer = response_body['content'][0]['text']
            
            # Calculate overall confidence based on retrieval scores
            avg_confidence = sum(r['confidence'] for r in retrieval_results) / len(retrieval_results)
            
            return {
                'answer': answer.strip(),
                'confidence': avg_confidence
            }
            
        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return {
                'answer': 'I encountered an error while generating an answer from the knowledge base.',
                'confidence': 0.0
            }
    
    def _format_sources(self, retrieval_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Format source information for response.
        
        Args:
            retrieval_results: Retrieved document chunks
            
        Returns:
            List of formatted source references
        """
        sources = []
        for i, result in enumerate(retrieval_results):
            source_info = {
                'id': i + 1,
                'confidence': result['confidence'],
                'excerpt': result['content'][:200] + '...' if len(result['content']) > 200 else result['content']
            }
            
            # Add source URI if available
            if result.get('source'):
                source_info['uri'] = result['source']
            
            # Add metadata if available
            if result.get('metadata'):
                source_info['metadata'] = result['metadata']
            
            sources.append(source_info)
        
        return sources
    
    def get_schema(self) -> Dict[str, Any]:
        """
        Return the tool schema for agent framework integration.
        
        Returns:
            JSON schema describing the tool's parameters and usage
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or question for the knowledge base"
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                        "description": "Maximum number of results to retrieve"
                    },
                    "include_sources": {
                        "type": "boolean",
                        "default": True,
                        "description": "Whether to include source references in the response"
                    }
                },
                "required": ["query"]
            }
        }


# Enhanced knowledge base tool with caching and advanced features
class EnhancedKnowledgeBaseTool(KnowledgeBaseTool):
    """
    Enhanced version of KnowledgeBaseTool with caching and advanced query features.
    
    This implementation adds response caching, query preprocessing, and
    advanced filtering capabilities for improved performance and accuracy.
    """
    
    def __init__(self):
        """Initialize enhanced tool with caching capabilities."""
        super().__init__()
        
        # Simple in-memory cache (in production, use Redis or similar)
        self._cache = {}
        self.cache_ttl = int(os.getenv('KB_CACHE_TTL', '3600'))  # 1 hour default
        
        logger.info("Enhanced KnowledgeBaseTool initialized with caching")
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute knowledge base query with caching and preprocessing.
        
        Args:
            parameters: Query parameters
            
        Returns:
            Cached or newly generated response
        """
        query = parameters.get('query', '').strip()
        
        # Check cache first
        cache_key = self._generate_cache_key(query, parameters)
        cached_response = self._get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"Returning cached response for query: {query[:50]}...")
            return cached_response
        
        # Preprocess query for better results
        processed_query = self._preprocess_query(query)
        parameters['query'] = processed_query
        
        # Execute original logic
        response = await super().execute(parameters)
        
        # Cache successful responses
        if response.get('statusCode') == 200:
            self._cache_response(cache_key, response)
        
        return response
    
    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess query to improve search results.
        
        Args:
            query: Original query
            
        Returns:
            Preprocessed query
        """
        # Add ITSM context if not present
        itsm_keywords = ['ticket', 'incident', 'request', 'change', 'problem', 'service']
        
        if not any(keyword in query.lower() for keyword in itsm_keywords):
            # Add ITSM context to improve relevance
            query = f"ITSM IT service management: {query}"
        
        return query
    
    def _generate_cache_key(self, query: str, parameters: Dict[str, Any]) -> str:
        """Generate cache key for query and parameters."""
        import hashlib
        
        # Create deterministic key from query and relevant parameters
        key_data = {
            'query': query.lower().strip(),
            'max_results': parameters.get('max_results', self.max_results),
            'kb_id': self.knowledge_base_id
        }
        
        key_string = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available and not expired."""
        import time
        
        if cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if time.time() - cached_item['timestamp'] < self.cache_ttl:
                return cached_item['response']
            else:
                # Remove expired item
                del self._cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: Dict[str, Any]) -> None:
        """Cache response with timestamp."""
        import time
        
        self._cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        
        # Simple cache size management (keep last 100 items)
        if len(self._cache) > 100:
            oldest_key = min(self._cache.keys(), 
                           key=lambda k: self._cache[k]['timestamp'])
            del self._cache[oldest_key]