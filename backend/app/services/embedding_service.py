"""Embedding generation service using OpenAI."""

from typing import List
from openai import AsyncOpenAI
from app.config import settings
from app.utils.logger import get_logger
from app.utils.error_handler import handle_service_errors

logger = get_logger(__name__)


class EmbeddingService:
    """Service for generating text embeddings."""

    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.embedding_model

    @handle_service_errors("embedding_generation")
    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """

        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
            encoding_format="float"
        )

        embedding = response.data[0].embedding

        logger.debug(
            "embedding_generated",
            text_length=len(text),
            embedding_dim=len(embedding)
        )

        return embedding

    @handle_service_errors("batch_embedding_generation")
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """

        response = await self.client.embeddings.create(
            model=self.model,
            input=texts,
            encoding_format="float"
        )

        embeddings = [item.embedding for item in response.data]

        logger.info(
            "batch_embeddings_generated",
            count=len(embeddings)
        )

        return embeddings
