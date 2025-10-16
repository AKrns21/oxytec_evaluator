"""RAG service for querying the product database."""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.embedding_service import EmbeddingService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProductRAGService:
    """Service for semantic search over the product database."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize RAG service.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.embedding_service = EmbeddingService()

    async def search_products(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over product database using pgvector.

        Args:
            query: Natural language query
            top_k: Number of results to return
            category_filter: Optional category filter

        Returns:
            List of relevant products with similarity scores
        """

        logger.info("product_search_started", query=query[:100])

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed(query)

            # Build SQL query with vector similarity search
            sql_query = text("""
                SELECT
                    p.id,
                    p.name,
                    p.category,
                    p.technical_specs,
                    pe.chunk_text,
                    pe.chunk_metadata,
                    1 - (pe.embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM product_embeddings pe
                JOIN products p ON pe.product_id = p.id
                WHERE 1=1
                    AND (:category_filter IS NULL OR p.category = :category_filter)
                ORDER BY pe.embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
            """)

            # Execute query
            result = await self.db.execute(
                sql_query,
                {
                    "query_embedding": str(query_embedding),
                    "category_filter": category_filter,
                    "top_k": top_k
                }
            )

            rows = result.fetchall()

            # Format results
            products = []
            for row in rows:
                products.append({
                    "product_id": str(row.id),
                    "product_name": row.name,
                    "category": row.category,
                    "technical_specs": row.technical_specs,
                    "relevant_chunk": row.chunk_text,
                    "metadata": row.chunk_metadata,
                    "similarity": float(row.similarity)
                })

            logger.info(
                "product_search_completed",
                query=query[:100],
                results_count=len(products)
            )

            return products

        except Exception as e:
            logger.error("product_search_failed", query=query, error=str(e))
            raise

    async def get_product_details(self, product_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete product information by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product details or None if not found
        """

        try:
            sql_query = text("""
                SELECT id, name, category, technical_specs, description
                FROM products
                WHERE id = :product_id
            """)

            result = await self.db.execute(sql_query, {"product_id": product_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                "id": str(row.id),
                "name": row.name,
                "category": row.category,
                "technical_specs": row.technical_specs,
                "description": row.description
            }

        except Exception as e:
            logger.error("product_details_failed", product_id=product_id, error=str(e))
            raise
