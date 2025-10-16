"""Document processing service for extracting text from various formats."""

import os
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
        """Extract text from PDF using PyMuPDF."""
        try:
            doc = fitz.open(file_path)
            text_parts = []

            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    text_parts.append(f"--- Page {page_num} ---\n{text}")

            doc.close()
            return "\n\n".join(text_parts)

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
