"""
Ingest oxytec technology knowledge from scope_oxytec_industry.json into vector store.

This script parses the catalog JSON and creates semantic chunks with embeddings for RAG.

Chunking Strategy:
- Header chunks: rubric + title (for high-level technology matching)
- Description chunks: Main body text in ~500 char segments
- Application chunks: Each application example separately
- Technical data chunks: Each product with its specs
- Process chunks: Step-by-step processes
- Function chunks: "Funktion", "Einsatz", "Technologie & Material" sections

Usage:
    python scripts/ingest_technology_knowledge.py --source docs/scope_oxytec_industry.json
    python scripts/ingest_technology_knowledge.py --source docs/scope_oxytec_industry.json --clear
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text, select
from app.db.session import AsyncSessionLocal
from app.models.database import TechnologyKnowledge, TechnologyEmbedding
from app.services.embedding_service import EmbeddingService
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Chunking configuration
CHUNK_SIZE = 1000  # Maximum characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks for context continuity


# Technology type classification based on rubric/title keywords
TECHNOLOGY_CLASSIFIERS = {
    'uv_ozone': ['uv/ozon', 'uv ozon', 'fotolyse', 'fotooxidation', 'cea', 'cfa'],
    'scrubber': ['wäscher', 'scrubber', 'cwa', 'csa', 'gegenstrom', 'rauchwäscher'],
    'heat_recovery': ['wärmerückgewinnung', 'heat recovery', 'aah'],
    'catalyst': ['katalysator', 'kat ', 'speicherreaktor', 'aktivkohle'],
    'hybrid': ['kombination', 'verfahrenskombination', 'multi-stage'],
    'electrostatic': ['elektrostatisch', 'esw'],
}

# Pollutant detection keywords
POLLUTANT_KEYWORDS = {
    'VOC': ['voc', 'organisch', 'ges-c', 'gesamt c', 'tvoc'],
    'formaldehyde': ['formaldehyd'],
    'H2S': ['h₂s', 'h2s', 'schwefelwasserstoff'],
    'ammonia': ['ammoniak', 'nh₃', 'nh3'],
    'SO2': ['so₂', 'so2', 'schwefeldioxid'],
    'odor': ['geruch', 'geruchsemission', 'ge'],
    'fett': ['fett', 'fettig', 'oil', 'öl'],
    'keime': ['keim', 'bakterien', 'bioaerosol'],
    'particulates': ['partikel', 'staub', 'aerosol'],
    'teer': ['teer', 'tar'],
}

# Industry detection keywords
INDUSTRY_KEYWORDS = {
    'food_processing': ['lebensmittel', 'food', 'fritteur', 'bräter', 'fleisch', 'räucher', 'schlachthof'],
    'wastewater': ['kläranlage', 'klärschlamm', 'wastewater', 'abwasser'],
    'chemical': ['chemical', 'chemisch', 'heparin'],
    'textile': ['textil', 'beschichtung'],
    'printing': ['druck', 'printing'],
    'agriculture': ['stall', 'tierhaltung', 'livestock', 'biogas'],
    'rendering': ['tierkörperverwertung', 'rendering'],
}


def classify_technology_type(page_data: Dict[str, Any]) -> str:
    """Classify technology type based on rubric and title."""
    text = (
        page_data.get('title_block', {}).get('rubric', '') + ' ' +
        page_data.get('title_block', {}).get('title', '')
    ).lower()

    for tech_type, keywords in TECHNOLOGY_CLASSIFIERS.items():
        if any(kw in text for kw in keywords):
            return tech_type

    return 'general'


def extract_pollutants(text: str) -> List[str]:
    """Extract pollutant types mentioned in text."""
    text_lower = text.lower()
    found = []

    for pollutant, keywords in POLLUTANT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(pollutant)

    return list(set(found))


def extract_industries(text: str) -> List[str]:
    """Extract industry types mentioned in text."""
    text_lower = text.lower()
    found = []

    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(industry)

    return list(set(found))


def extract_product_names(text: str) -> List[str]:
    """Extract oxytec product names mentioned in text."""
    product_pattern = ['CEA', 'CFA', 'CWA', 'CSA', 'KAT', 'AAH', 'ESW']
    found = []

    for product in product_pattern:
        if product in text.upper():
            found.append(product)

    return list(set(found))


def chunk_text(text: str, max_length: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Recursive character text splitter with configurable size and overlap.

    Tries to split text on natural boundaries in order:
    1. Double newlines (paragraphs)
    2. Single newlines (lines)
    3. Sentence endings (. ! ?)
    4. Commas
    5. Spaces
    6. Character-by-character (fallback)

    Args:
        text: Text to split
        max_length: Maximum characters per chunk (default: CHUNK_SIZE)
        overlap: Overlap between chunks for context (default: CHUNK_OVERLAP)

    Returns:
        List of text chunks
    """
    if len(text) <= max_length:
        return [text]

    # Define separators in order of preference (most natural to least)
    separators = ['\n\n', '\n', '. ', '! ', '? ', ', ', ' ', '']

    chunks = []
    start = 0

    while start < len(text):
        # Determine the end position for this chunk
        end = min(start + max_length, len(text))

        # If we're at the end of text, take everything remaining
        if end == len(text):
            chunks.append(text[start:end].strip())
            break

        # Try to find a natural break point using separators
        best_split = end
        for separator in separators:
            if separator == '':
                # Fallback: no separator, hard cut
                best_split = end
                break

            # Look for the separator within the chunk
            split_pos = text.rfind(separator, start, end)

            # Accept the split if it's not too close to the start
            # (avoid tiny chunks - require at least 20% of max_length)
            if split_pos > start + (max_length // 5):
                best_split = split_pos + len(separator)
                break

        # Extract the chunk
        chunk = text[start:best_split].strip()
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)

        # Move start position with overlap, ensuring we always make progress
        new_start = best_split - overlap
        start = max(new_start, start + 1)  # Guarantee forward progress

    return chunks


def create_chunks_from_page(page_number: int, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create semantic chunks from a page of data."""
    chunks = []

    title_block = page_data.get('title_block', {})
    rubric = title_block.get('rubric', '')
    title = title_block.get('title', '')

    # Chunk 1: Header (always create this)
    header_text = f"{rubric}: {title}" if rubric else title
    chunks.append({
        'chunk_type': 'header',
        'text': header_text,
        'metadata': {
            'page_number': page_number,
            'rubric': rubric,
            'title': title,
        }
    })

    # Chunk 2: Left column (if exists)
    left_column = page_data.get('left_column', [])
    if left_column:
        left_text = '\n'.join(left_column)
        for i, text_chunk in enumerate(chunk_text(left_text)):
            chunks.append({
                'chunk_type': 'description',
                'text': f"{header_text}\n\n{text_chunk}",
                'metadata': {
                    'page_number': page_number,
                    'section': 'left_column',
                    'chunk_index': i,
                }
            })

    # Chunk 3: Right column (if exists)
    right_column = page_data.get('right_column', [])
    if right_column:
        right_text = '\n'.join(right_column)
        for i, text_chunk in enumerate(chunk_text(right_text)):
            chunks.append({
                'chunk_type': 'description',
                'text': f"{header_text}\n\n{text_chunk}",
                'metadata': {
                    'page_number': page_number,
                    'section': 'right_column',
                    'chunk_index': i,
                }
            })

    # Chunk 4: Body text (if exists)
    body = page_data.get('body', [])
    if body:
        body_text = '\n'.join(body)
        for i, text_chunk in enumerate(chunk_text(body_text)):
            chunks.append({
                'chunk_type': 'application_example' if 'anwendung' in title.lower() else 'description',
                'text': f"{header_text}\n\n{text_chunk}",
                'metadata': {
                    'page_number': page_number,
                    'section': 'body',
                    'chunk_index': i,
                }
            })

    # Chunk 5: Sections (if exists - structured content)
    sections = page_data.get('sections', {})
    for section_name, section_items in sections.items():
        if isinstance(section_items, list):
            section_text = '\n'.join(section_items)
            chunks.append({
                'chunk_type': 'function' if 'funktion' in section_name.lower() else 'description',
                'text': f"{header_text} - {section_name}\n\n{section_text}",
                'metadata': {
                    'page_number': page_number,
                    'section': section_name,
                }
            })

    # Chunk 6: Tables (if exists)
    tables = page_data.get('tables', []) or ([page_data.get('table')] if page_data.get('table') else [])
    for table_idx, table in enumerate(tables):
        if not table:
            continue

        # Format table as text
        table_text = f"{header_text}\n\nTechnische Daten:\n"
        if table.get('caption'):
            table_text += f"{table['caption']}\n"

        columns = table.get('columns', [])
        rows = table.get('rows', [])

        if columns and rows:
            # Create table string
            for row in rows:
                if isinstance(row, dict):
                    # Table with labeled rows
                    row_text = f"{row.get('label', '')}:"
                    for col in columns:
                        if col in row:
                            row_text += f" {col}={row[col]}"
                    table_text += f"  {row_text}\n"
                elif isinstance(row, list):
                    # Simple table
                    row_text = " | ".join(str(cell) for cell in row)
                    table_text += f"  {row_text}\n"

        chunks.append({
            'chunk_type': 'technical_data',
            'text': table_text,
            'metadata': {
                'page_number': page_number,
                'table_index': table_idx,
                'has_specs': True,
            }
        })

    return chunks


async def ingest_knowledge(source_path: Path, clear_existing: bool = False):
    """Ingest technology knowledge from JSON file."""

    logger.info("ingestion_started", source=str(source_path), clear_existing=clear_existing)
    print(f"📖 Loading technology knowledge from {source_path}", flush=True)

    # Load JSON
    with open(source_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ Loaded {len(data)} pages from catalog", flush=True)

    # Initialize services
    embedding_service = EmbeddingService()

    async with AsyncSessionLocal() as db:
        try:
            # Clear existing data if requested
            if clear_existing:
                print("🗑️  Clearing existing technology knowledge...", flush=True)
                await db.execute(text("DELETE FROM technology_embeddings"))
                await db.execute(text("DELETE FROM technology_knowledge"))
                await db.commit()
                print("✅ Existing data cleared", flush=True)

            # Process each page
            total_chunks = 0

            for page_num_str, page_data in data.items():
                page_num = int(page_num_str)
                print(f"\n📄 Processing page {page_num}...", flush=True)

                # Extract metadata
                title_block = page_data.get('title_block', {})
                rubric = title_block.get('rubric', '')
                title = title_block.get('title', '')

                if not title:
                    logger.warning("page_missing_title", page=page_num)
                    continue

                tech_type = classify_technology_type(page_data)

                # Combine all text for pollutant/industry extraction
                all_text = json.dumps(page_data, ensure_ascii=False)
                pollutants = extract_pollutants(all_text)
                industries = extract_industries(all_text)
                products = extract_product_names(all_text)

                # Create TechnologyKnowledge record
                tech_knowledge = TechnologyKnowledge(
                    id=uuid4(),
                    page_number=page_num,
                    rubric=rubric,
                    title=title,
                    technology_type=tech_type,
                    content=page_data,
                    pollutant_types=pollutants if pollutants else None,
                    industries=industries if industries else None,
                    products_mentioned=products if products else None,
                )

                db.add(tech_knowledge)
                await db.flush()  # Get ID

                print(f"  ℹ️  Type: {tech_type}, Pollutants: {pollutants}, Industries: {industries}", flush=True)

                # Create chunks
                chunks = create_chunks_from_page(page_num, page_data)
                print(f"  📦 Created {len(chunks)} chunks", flush=True)

                # Generate embeddings and store
                for chunk in chunks:
                    # Generate embedding
                    embedding = await embedding_service.embed(chunk['text'])

                    # Enhance metadata with extracted info
                    chunk['metadata']['pollutants'] = pollutants
                    chunk['metadata']['industries'] = industries
                    chunk['metadata']['products'] = products
                    chunk['metadata']['technology_type'] = tech_type

                    tech_embedding = TechnologyEmbedding(
                        technology_id=tech_knowledge.id,
                        chunk_type=chunk['chunk_type'],
                        chunk_text=chunk['text'],
                        chunk_metadata=chunk['metadata'],
                        embedding=embedding,
                    )

                    db.add(tech_embedding)
                    total_chunks += 1

                # Commit after each page
                await db.commit()
                print(f"  ✅ Page {page_num} committed", flush=True)

            print(f"\n🎉 Ingestion completed!", flush=True)
            print(f"  📚 Pages processed: {len(data)}", flush=True)
            print(f"  📦 Total chunks created: {total_chunks}", flush=True)
            print(f"  🔢 Average chunks per page: {total_chunks / len(data):.1f}", flush=True)

            logger.info(
                "ingestion_completed",
                pages=len(data),
                chunks=total_chunks,
                avg_chunks_per_page=total_chunks / len(data)
            )

        except Exception as e:
            await db.rollback()
            logger.error("ingestion_failed", error=str(e))
            print(f"\n❌ Ingestion failed: {e}", flush=True)
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest oxytec technology knowledge")
    parser.add_argument(
        "--source",
        type=str,
        default="docs/scope_oxytec_industry.json",
        help="Path to scope_oxytec_industry.json file"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing technology knowledge before ingestion"
    )

    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"❌ Error: Source file not found: {source_path}", flush=True)
        sys.exit(1)

    asyncio.run(ingest_knowledge(source_path, clear_existing=args.clear))
