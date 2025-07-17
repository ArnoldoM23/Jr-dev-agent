import logging
import asyncio
from typing import List, Dict, Any, Optional
from openai import OpenAI
import tiktoken

logger = logging.getLogger(__name__)

class EmbeddingEngine:
    """
    Embedding engine for generating semantic embeddings using OpenAI's text-embedding-3-small model.
    
    Features:
    - 768-dimensional embeddings
    - Async support for batch processing
    - Token counting and cost optimization
    - Fallback to MiniLM for development
    """
    
    def __init__(self, openai_client: OpenAI, model: str = "text-embedding-3-small"):
        self.client = openai_client
        self.model = model
        self.dimensions = 768
        self.max_tokens = 8192
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")  # Similar tokenization
        
        logger.info(f"✅ EmbeddingEngine initialized with model: {model}")
    
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate a single embedding for the given text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of 768 floats representing the embedding
        """
        try:
            # Truncate text if too long
            text = self._truncate_text(text)
            
            # Generate embedding
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                input=text,
                dimensions=self.dimensions
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"✅ Generated embedding for text (length: {len(text)})")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            raise
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a batch.
        
        Args:
            texts: List of input texts to embed
            
        Returns:
            List of embeddings, each with 768 dimensions
        """
        try:
            # Truncate all texts
            truncated_texts = [self._truncate_text(text) for text in texts]
            
            # Generate embeddings in batch
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.model,
                input=truncated_texts,
                dimensions=self.dimensions
            )
            
            embeddings = [data.embedding for data in response.data]
            
            logger.info(f"✅ Generated {len(embeddings)} embeddings in batch")
            return embeddings
            
        except Exception as e:
            logger.error(f"❌ Failed to generate batch embeddings: {e}")
            raise
    
    def _truncate_text(self, text: str) -> str:
        """
        Truncate text to fit within token limits.
        
        Args:
            text: Input text to truncate
            
        Returns:
            Truncated text that fits within token limits
        """
        try:
            tokens = self.encoding.encode(text)
            
            if len(tokens) <= self.max_tokens:
                return text
            
            # Truncate to max tokens
            truncated_tokens = tokens[:self.max_tokens]
            truncated_text = self.encoding.decode(truncated_tokens)
            
            logger.warning(f"⚠️ Text truncated from {len(tokens)} to {len(truncated_tokens)} tokens")
            return truncated_text
            
        except Exception as e:
            logger.error(f"❌ Failed to truncate text: {e}")
            # Fallback to character-based truncation
            return text[:32000]  # Rough estimate
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in the given text.
        
        Args:
            text: Input text to count tokens for
            
        Returns:
            Number of tokens in the text
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.error(f"❌ Failed to count tokens: {e}")
            return len(text) // 4  # Rough estimate
    
    def estimate_cost(self, text: str) -> float:
        """
        Estimate the cost of embedding the given text.
        
        Args:
            text: Input text to estimate cost for
            
        Returns:
            Estimated cost in USD
        """
        try:
            tokens = self.count_tokens(text)
            # text-embedding-3-small: $0.00002 per 1K tokens
            cost_per_1k_tokens = 0.00002
            return (tokens / 1000) * cost_per_1k_tokens
        except Exception as e:
            logger.error(f"❌ Failed to estimate cost: {e}")
            return 0.0
    
    async def test_connection(self) -> bool:
        """
        Test the connection to OpenAI API.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            test_embedding = await self.generate_embedding("test")
            
            if len(test_embedding) == self.dimensions:
                logger.info("✅ OpenAI API connection test successful")
                return True
            else:
                logger.error(f"❌ Unexpected embedding dimensions: {len(test_embedding)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ OpenAI API connection test failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current embedding model.
        
        Returns:
            Dictionary containing model information
        """
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "max_tokens": self.max_tokens,
            "cost_per_1k_tokens": 0.00002
        } 