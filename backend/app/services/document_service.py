"""Document processing service for extracting text from various formats."""

import os
import base64
from pathlib import Path
from typing import Optional
import fitz  # PyMuPDF
import docx
import pandas as pd
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DocumentService:
    """Service for extracting text from documents."""

    async def extract_text(self, file_path: str, mime_type: Optional[str] = None) -> str:
        """
        Extract text from a document.

        Supports: PDF, DOCX, TXT, CSV, XLSX

        Args:
            file_path: Path to the file
            mime_type: MIME type of the file (optional)

        Returns:
            Extracted text content
        """

        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        extension = path.suffix.lower()

        try:
            if extension == ".pdf":
                return await self._extract_pdf(file_path)
            elif extension in [".docx", ".doc"]:
                return await self._extract_docx(file_path)
            elif extension == ".txt":
                return await self._extract_txt(file_path)
            elif extension in [".csv", ".xlsx", ".xls"]:
                return await self._extract_spreadsheet(file_path)
            else:
                logger.warning("unsupported_file_type", extension=extension)
                return f"[Unsupported file type: {extension}]"

        except Exception as e:
            logger.error("text_extraction_failed", file_path=file_path, error=str(e))
            raise

    async def _extract_pdf(self, file_path: str) -> str:
        """Extract text from PDF using PyMuPDF, fallback to vision for image-based PDFs."""
        try:
            doc = fitz.open(file_path)
            text_parts = []
            image_based_pages = []

            # First, try regular text extraction
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")
                else:
                    # No text found, this might be an image-based page
                    image_based_pages.append((page_num, page))

            # If we got text from regular extraction, use it
            if text_parts:
                doc.close()
                return "\n\n".join(text_parts)

            # If no text was extracted, use vision to extract from images
            logger.info("pdf_is_image_based", file_path=file_path, pages=len(doc))

            # Extract using vision for image-based PDFs (in parallel)
            import asyncio

            # Convert all pages to images first
            page_images = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality
                img_bytes = pix.tobytes("png")
                page_images.append((page_num + 1, img_bytes))

            # Extract text from all pages in parallel
            vision_tasks = [
                self._extract_text_from_image_with_vision(
                    img_bytes,
                    f"page_{page_num}"
                )
                for page_num, img_bytes in page_images
            ]

            vision_results = await asyncio.gather(*vision_tasks, return_exceptions=True)

            # Collect results
            vision_text_parts = []
            for idx, (page_num, _) in enumerate(page_images):
                result = vision_results[idx]
                if isinstance(result, Exception):
                    logger.error("vision_page_failed", page=page_num, error=str(result))
                    vision_text_parts.append(f"--- Page {page_num} ---\n[Vision extraction failed: {str(result)}]")
                elif result.strip():
                    vision_text_parts.append(f"--- Page {page_num} ---\n{result}")

            doc.close()

            if vision_text_parts:
                logger.info("pdf_extracted_with_vision", pages=len(vision_text_parts))
                return "\n\n".join(vision_text_parts)
            else:
                logger.warning("pdf_no_content_extracted", file_path=file_path)
                return "[No text content could be extracted from this PDF]"

        except Exception as e:
            logger.error("pdf_extraction_failed", error=str(e))
            raise

    async def _extract_docx(self, file_path: str) -> str:
        """Extract text from DOCX."""
        try:
            doc = docx.Document(file_path)
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]

            # Also extract text from tables
            tables_text = []
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join(cell.text.strip() for cell in row.cells)
                    if row_text.strip():
                        tables_text.append(row_text)

            all_text = paragraphs
            if tables_text:
                all_text.append("\n--- Tables ---\n")
                all_text.extend(tables_text)

            return "\n".join(all_text)

        except Exception as e:
            logger.error("docx_extraction_failed", error=str(e))
            raise

    async def _extract_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(file_path, "r", encoding="latin-1") as f:
                return f.read()

    async def _extract_spreadsheet(self, file_path: str) -> str:
        """Extract text from CSV/Excel."""
        try:
            extension = Path(file_path).suffix.lower()

            if extension == ".csv":
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Convert DataFrame to readable text
            text_parts = [
                f"Spreadsheet with {len(df)} rows and {len(df.columns)} columns",
                f"\nColumns: {', '.join(df.columns.tolist())}",
                "\n--- Data Preview (first 50 rows) ---",
                df.head(50).to_string(index=False)
            ]

            return "\n".join(text_parts)

        except Exception as e:
            logger.error("spreadsheet_extraction_failed", error=str(e))
            raise

    async def _extract_text_from_image_with_vision(
        self,
        image_bytes: bytes,
        page_identifier: str
    ) -> str:
        """
        Extract text from an image using Claude's vision API.

        Args:
            image_bytes: Image data as bytes (PNG format)
            page_identifier: Identifier for logging (e.g., "page_1")

        Returns:
            Extracted text content
        """
        try:
            from anthropic import AsyncAnthropic
            from app.config import settings

            # Encode image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')

            # Use Claude with vision
            client = AsyncAnthropic(api_key=settings.anthropic_api_key)

            response = await client.messages.create(
                model=settings.anthropic_model,
                max_tokens=4096,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": "Extract all text content from this document image. Preserve the structure, tables, and formatting as much as possible. Return only the extracted text, without any commentary or explanation."
                        }
                    ]
                }]
            )

            extracted_text = response.content[0].text

            logger.info(
                "vision_extraction_success",
                page=page_identifier,
                length=len(extracted_text)
            )

            return extracted_text

        except Exception as e:
            logger.error(
                "vision_extraction_failed",
                page=page_identifier,
                error=str(e)
            )
            return f"[Vision extraction failed for {page_identifier}: {str(e)}]"
