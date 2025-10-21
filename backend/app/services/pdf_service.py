"""PDF generation service for feasibility reports."""

import io
import re
import markdown
from xhtml2pdf import pisa
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PDFService:
    """Service for generating PDF reports from markdown content."""

    def _normalize_subscripts(self, text: str) -> str:
        """
        Convert Unicode subscript characters to HTML <sub> tags.

        This is the elegant solution: handle it once at the input level.
        """
        # Unicode subscript mapping
        subscript_map = str.maketrans(
            '₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ',
            '0123456789aehijklmnoprstuvx'
        )

        # Replace Unicode subscripts with <sub>x</sub>
        def replace_subscript(match):
            char = match.group(0)
            normal_char = char.translate(subscript_map)
            return f'<sub>{normal_char}</sub>'

        # Pattern for any Unicode subscript character
        pattern = '[₀₁₂₃₄₅₆₇₈₉ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ]'
        text = re.sub(pattern, replace_subscript, text)

        # Replace emoji icons with HTML colored text (Unicode filled circle)
        # Using ● (U+25CF BLACK CIRCLE) with color styling
        text = text.replace('🟢', '<span style="color: #00a000; font-size: 14pt;">●</span>')
        text = text.replace('🟡', '<span style="color: #ffa500; font-size: 14pt;">●</span>')
        text = text.replace('🔴', '<span style="color: #ff0000; font-size: 14pt;">●</span>')

        return text

    def generate_pdf(self, markdown_content: str, title: str = "Machbarkeitsstudie") -> bytes:
        """
        Generate a PDF from markdown content using xhtml2pdf.

        Args:
            markdown_content: The markdown content to convert
            title: Optional title for the document

        Returns:
            PDF content as bytes

        Raises:
            Exception: If PDF generation fails
        """
        try:
            # First, normalize Unicode subscripts to HTML
            normalized_markdown = self._normalize_subscripts(markdown_content)

            # Convert markdown to HTML
            html_body = markdown.markdown(
                normalized_markdown,
                extensions=['tables', 'fenced_code', 'nl2br']
            )

            # Create full HTML document with CSS styling
            html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm;
        }}

        @font-face {{
            font-family: 'Roboto';
            src: local('Roboto'), local('Arial'), local('Helvetica');
        }}

        body {{
            font-family: 'Roboto', Arial, sans-serif;
            font-size: 11pt;
            line-height: 1.3;
            color: #333;
        }}

        h1 {{
            font-size: 24pt;
            font-weight: bold;
            color: #1a56db;
            margin-bottom: 10pt;
            padding-bottom: 8pt;
            border-bottom: 2pt solid #333;
        }}

        h2 {{
            font-size: 14pt;
            font-weight: bold;
            color: #1a56db;
            margin-top: 20pt;
            margin-bottom: 12pt;
        }}

        h3 {{
            font-size: 11pt;
            font-weight: bold;
            color: #000;
            margin-top: 14pt;
            margin-bottom: 10pt;
        }}

        p {{
            margin-bottom: 10pt;
            text-align: justify;
            line-height: 1.3;
        }}

        ul {{
            margin: 10pt 0;
            padding-left: 0;
            list-style-position: outside;
        }}

        li {{
            margin-left: 20pt;
            margin-bottom: 8pt;
            line-height: 1.3;
            padding-left: 5pt;
        }}

        strong {{
            font-weight: bold;
            color: #000;
        }}

        /* Style for the rating emoji/icon */
        .rating {{
            display: inline-block;
            width: 12pt;
            height: 12pt;
            border-radius: 50%;
            margin-right: 4pt;
            vertical-align: middle;
        }}

        .rating-machbar {{
            background-color: #ffa500;
        }}

        .rating-gut {{
            background-color: #00a000;
        }}

        .rating-schwierig {{
            background-color: #ff0000;
        }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {html_body}
</body>
</html>
"""

            # Generate PDF
            pdf_buffer = io.BytesIO()
            pisa_status = pisa.CreatePDF(
                html.encode('utf-8'),
                dest=pdf_buffer,
                encoding='utf-8'
            )

            if pisa_status.err:
                raise Exception(f"PDF generation error: {pisa_status.err}")

            pdf_bytes = pdf_buffer.getvalue()
            pdf_buffer.close()

            logger.info(
                "pdf_generated",
                content_length=len(markdown_content),
                pdf_size=len(pdf_bytes)
            )

            return pdf_bytes

        except Exception as e:
            logger.error("pdf_generation_failed", error=str(e))
            raise Exception(f"Failed to generate PDF: {str(e)}")
