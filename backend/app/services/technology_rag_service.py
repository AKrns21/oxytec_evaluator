"""RAG service for querying the oxytec technology knowledge base."""

from typing import List, Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.embedding_service import EmbeddingService
from app.utils.logger import get_logger
from app.utils.error_handler import handle_service_errors

logger = get_logger(__name__)


class TechnologyRAGService:
    """Service for semantic search over oxytec technology knowledge base."""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize RAG service.

        Args:
            db_session: Database session
        """
        self.db = db_session
        self.embedding_service = EmbeddingService()

    @handle_service_errors("technology_knowledge_search")
    async def search_knowledge(
        self,
        query: str,
        top_k: int = 5,
        technology_type: Optional[str] = None,
        pollutant_filter: Optional[str] = None,
        industry_filter: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over technology knowledge base using pgvector.

        Args:
            query: Natural language query (e.g., "UV ozone formaldehyde removal efficiency")
            top_k: Number of results to return (default: 5)
            technology_type: Optional filter by technology type
                ('uv_ozone', 'scrubber', 'catalyst', 'hybrid', etc.)
            pollutant_filter: Optional filter by pollutant type
                ('VOC', 'formaldehyde', 'H2S', 'ammonia', etc.)
            industry_filter: Optional filter by industry
                ('food_processing', 'wastewater', 'textile', etc.)
            chunk_type: Optional filter by chunk type
                ('header', 'description', 'application_example', 'technical_data', etc.)

        Returns:
            List of relevant knowledge chunks with similarity scores
        """

        logger.info(
            "technology_search_started",
            query=query[:100],
            technology_type=technology_type,
            pollutant=pollutant_filter,
            industry=industry_filter
        )

        # Generate query embedding
        query_embedding = await self.embedding_service.embed(query)

        # Build dynamic WHERE clauses
        where_clauses = ["1=1"]
        params = {
            "query_embedding": str(query_embedding),
            "top_k": top_k
        }

        if technology_type:
            where_clauses.append("tk.technology_type = :technology_type")
            params["technology_type"] = technology_type

        if pollutant_filter:
            # JSONB arrays need to be accessed as JSON text arrays, not native PostgreSQL arrays
            where_clauses.append("tk.pollutant_types ? :pollutant")
            params["pollutant"] = pollutant_filter

        if industry_filter:
            # JSONB arrays need to be accessed as JSON text arrays, not native PostgreSQL arrays
            where_clauses.append("tk.industries ? :industry")
            params["industry"] = industry_filter

        if chunk_type:
            where_clauses.append("te.chunk_type = :chunk_type")
            params["chunk_type"] = chunk_type

        where_sql = " AND ".join(where_clauses)

        # Build SQL query with vector similarity search
        sql_query = text(f"""
            SELECT
                tk.id as knowledge_id,
                tk.page_number,
                tk.rubric,
                tk.title,
                tk.technology_type,
                tk.pollutant_types,
                tk.industries,
                tk.products_mentioned,
                te.chunk_type,
                te.chunk_text,
                te.chunk_metadata,
                1 - (te.embedding <=> CAST(:query_embedding AS vector)) as similarity
            FROM technology_embeddings te
            JOIN technology_knowledge tk ON te.technology_id = tk.id
            WHERE {where_sql}
            ORDER BY te.embedding <=> CAST(:query_embedding AS vector)
            LIMIT :top_k
        """)

        # Execute query
        result = await self.db.execute(sql_query, params)
        rows = result.fetchall()

        # Format results
        knowledge_chunks = []
        for row in rows:
            knowledge_chunks.append({
                "knowledge_id": str(row.knowledge_id),
                "page_number": row.page_number,
                "rubric": row.rubric,
                "title": row.title,
                "technology_type": row.technology_type,
                "pollutant_types": row.pollutant_types or [],
                "industries": row.industries or [],
                "products_mentioned": row.products_mentioned or [],
                "chunk_type": row.chunk_type,
                "chunk_text": row.chunk_text,
                "chunk_metadata": row.chunk_metadata,
                "similarity": float(row.similarity)
            })

        logger.info(
            "technology_search_completed",
            query=query[:100],
            results_count=len(knowledge_chunks),
            avg_similarity=sum(r["similarity"] for r in knowledge_chunks) / len(knowledge_chunks) if knowledge_chunks else 0
        )

        return knowledge_chunks

    @handle_service_errors("technology_knowledge_by_page")
    async def get_knowledge_by_page(self, page_number: int) -> Optional[Dict[str, Any]]:
        """
        Get complete technology knowledge for a specific page.

        Args:
            page_number: Catalog page number

        Returns:
            Technology knowledge details or None if not found
        """

        sql_query = text("""
            SELECT
                id,
                page_number,
                rubric,
                title,
                technology_type,
                content,
                pollutant_types,
                industries,
                products_mentioned
            FROM technology_knowledge
            WHERE page_number = :page_number
        """)

        result = await self.db.execute(sql_query, {"page_number": page_number})
        row = result.fetchone()

        if not row:
            return None

        return {
            "id": str(row.id),
            "page_number": row.page_number,
            "rubric": row.rubric,
            "title": row.title,
            "technology_type": row.technology_type,
            "content": row.content,
            "pollutant_types": row.pollutant_types or [],
            "industries": row.industries or [],
            "products_mentioned": row.products_mentioned or []
        }

    @handle_service_errors("technologies_by_pollutant")
    async def get_technologies_by_pollutant(self, pollutant: str) -> List[Dict[str, Any]]:
        """
        Get all technologies that can handle a specific pollutant.

        Args:
            pollutant: Pollutant type (e.g., 'VOC', 'formaldehyde', 'H2S')

        Returns:
            List of technologies with their capabilities
        """

        # Use JSONB ? operator to check if pollutant exists in the JSONB array
        sql_query = text("""
            SELECT DISTINCT
                technology_type,
                title,
                page_number,
                products_mentioned
            FROM technology_knowledge
            WHERE pollutant_types ? :pollutant
            ORDER BY technology_type, page_number
        """)

        result = await self.db.execute(sql_query, {"pollutant": pollutant})
        rows = result.fetchall()

        technologies = []
        for row in rows:
            technologies.append({
                "technology_type": row.technology_type,
                "title": row.title,
                "page_number": row.page_number,
                "products_mentioned": row.products_mentioned or []
            })

        logger.info(
            "technologies_by_pollutant_retrieved",
            pollutant=pollutant,
            count=len(technologies)
        )

        return technologies

    @handle_service_errors("application_examples")
    async def get_application_examples(
        self,
        industry: Optional[str] = None,
        pollutant: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get application examples (case studies) filtered by industry/pollutant.

        Args:
            industry: Optional industry filter (e.g., 'food_processing', 'wastewater')
            pollutant: Optional pollutant filter (e.g., 'VOC', 'odor')

        Returns:
            List of application examples with details
        """

        where_clauses = ["te.chunk_type = 'application_example'"]
        params = {}

        if industry:
            # JSONB ? operator checks if key exists in JSONB array
            where_clauses.append("tk.industries ? :industry")
            params["industry"] = industry

        if pollutant:
            # JSONB ? operator checks if key exists in JSONB array
            where_clauses.append("tk.pollutant_types ? :pollutant")
            params["pollutant"] = pollutant

        where_sql = " AND ".join(where_clauses)

        sql_query = text(f"""
            SELECT DISTINCT
                tk.title,
                tk.page_number,
                tk.technology_type,
                tk.pollutant_types,
                tk.industries,
                te.chunk_text
            FROM technology_embeddings te
            JOIN technology_knowledge tk ON te.technology_id = tk.id
            WHERE {where_sql}
            ORDER BY tk.page_number
        """)

        result = await self.db.execute(sql_query, params)
        rows = result.fetchall()

        examples = []
        for row in rows:
            examples.append({
                "title": row.title,
                "page_number": row.page_number,
                "technology_type": row.technology_type,
                "pollutant_types": row.pollutant_types or [],
                "industries": row.industries or [],
                "description": row.chunk_text
            })

        logger.info(
            "application_examples_retrieved",
            industry=industry,
            pollutant=pollutant,
            count=len(examples)
        )

        return examples
