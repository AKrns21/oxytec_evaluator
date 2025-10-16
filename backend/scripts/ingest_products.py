"""Script to ingest product data into the database."""

import asyncio
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import AsyncSessionLocal
from app.models.database import Product, ProductEmbedding
from app.services.embedding_service import EmbeddingService
from app.utils.logger import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)


def chunk_product_content(product: Dict[str, Any], chunk_size: int = 500) -> List[Dict[str, Any]]:
    """
    Chunk product content for embedding generation.

    Args:
        product: Product dictionary
        chunk_size: Max characters per chunk

    Returns:
        List of chunks with text and metadata
    """

    chunks = []

    # Chunk 1: Product name and category
    chunk_text = f"Product: {product['name']}\nCategory: {product.get('category', 'N/A')}"
    chunks.append({
        "text": chunk_text,
        "metadata": {"type": "header", "product_name": product["name"]}
    })

    # Chunk 2: Description
    if product.get("description"):
        desc = product["description"]
        # Split long descriptions
        for i in range(0, len(desc), chunk_size):
            chunk_text = desc[i:i+chunk_size]
            chunks.append({
                "text": f"{product['name']}: {chunk_text}",
                "metadata": {"type": "description", "product_name": product["name"]}
            })

    # Chunk 3: Technical specifications
    if product.get("technical_specs"):
        specs_text = f"Technical Specifications for {product['name']}:\n"
        specs_text += "\n".join(
            f"- {key}: {value}"
            for key, value in product["technical_specs"].items()
        )
        chunks.append({
            "text": specs_text,
            "metadata": {"type": "specifications", "product_name": product["name"]}
        })

    return chunks


async def ingest_products(products_file: Path):
    """
    Ingest products from JSON file into database.

    Args:
        products_file: Path to products JSON file
    """

    logger.info("product_ingestion_started", file=str(products_file))

    # Load products from file
    with open(products_file, "r", encoding="utf-8") as f:
        products = json.load(f)

    if not isinstance(products, list):
        products = [products]

    logger.info("products_loaded", count=len(products))

    # Initialize services
    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as db:
        ingested_count = 0

        for product_data in products:
            try:
                logger.info("processing_product", name=product_data.get("name"))

                # Create product record
                product = Product(
                    name=product_data["name"],
                    category=product_data.get("category"),
                    technical_specs=product_data.get("technical_specs", {}),
                    description=product_data.get("description")
                )
                db.add(product)
                await db.flush()  # Get product ID

                # Chunk product content
                chunks = chunk_product_content(product_data)
                logger.info("product_chunked", name=product_data["name"], chunks=len(chunks))

                # Generate embeddings for each chunk
                for chunk in chunks:
                    embedding = await embedding_service.embed(chunk["text"])

                    product_embedding = ProductEmbedding(
                        product_id=product.id,
                        chunk_text=chunk["text"],
                        chunk_metadata=chunk["metadata"],
                        embedding=embedding
                    )
                    db.add(product_embedding)

                await db.commit()
                ingested_count += 1

                logger.info("product_ingested", name=product_data["name"])

            except Exception as e:
                logger.error(
                    "product_ingestion_failed",
                    name=product_data.get("name"),
                    error=str(e)
                )
                await db.rollback()
                continue

    logger.info("product_ingestion_completed", total=ingested_count)


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Ingest product data into database")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to products JSON file"
    )

    args = parser.parse_args()
    products_file = Path(args.source)

    if not products_file.exists():
        logger.error("file_not_found", path=str(products_file))
        sys.exit(1)

    await ingest_products(products_file)


if __name__ == "__main__":
    asyncio.run(main())
