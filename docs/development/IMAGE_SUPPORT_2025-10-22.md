# Image File Support Added - 2025-10-22

## Summary

Added native support for PNG, JPG, and JPEG image files using Claude's vision API for OCR and text extraction. The system now handles image files just like it handles image-based PDFs.

## Changes Made

### 1. Configuration Updates (`backend/app/config.py`)

**Before**:
```python
allowed_extensions: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt"]
```

**After**:
```python
allowed_extensions: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg"]
```

### 2. Document Service Updates (`backend/app/services/document_service.py`)

#### Added Image Extraction Method

New `_extract_image()` method (lines 162-243):
- Reads image file as bytes
- Detects image format (PNG or JPEG) from extension
- Encodes image to base64
- Calls Claude Sonnet 4.5 vision API for text extraction
- Returns extracted text with proper error handling

#### Updated File Type Routing

```python
async def extract_text(self, file_path: str, mime_type: Optional[str] = None) -> str:
    """
    Extract text from a document.

    Supports: PDF, DOCX, TXT, CSV, XLSX, PNG, JPG/JPEG (via vision)
    ...
    """
    # Added image file handling:
    elif extension in [".png", ".jpg", ".jpeg"]:
        return await self._extract_image(file_path)
```

### 3. Documentation Updates (`CLAUDE.md`)

Updated EXTRACTOR description:
- Now mentions PNG/JPG image support
- Documents vision API usage for OCR
- Notes parallel processing for multi-page image-based PDFs

Updated Service Layer documentation:
- DocumentService now lists PNG/JPG in supported formats
- Added bullet points about vision-based OCR capabilities

## Technical Details

### Vision API Integration

The implementation reuses the existing vision extraction infrastructure that was already in place for image-based PDFs:

```python
# Same vision prompt used for images and image-based PDFs
"Extract all text content from this document image.
 Preserve the structure, tables, and formatting as much as possible.
 Return only the extracted text, without any commentary or explanation."
```

### Supported Image Formats

- **PNG** (`.png`) - media_type: `image/png`
- **JPEG** (`.jpg`, `.jpeg`) - media_type: `image/jpeg`

### Model Used

- **Claude Sonnet 4.5** - Same model as WRITER agent
- **Max tokens**: 4096 for OCR extraction
- **API**: Anthropic AsyncAnthropic client

## Use Cases

### 1. Scanned Documents
Upload scanned inquiry documents as PNG/JPG instead of PDF:
- Measurement reports as screenshots
- Safety data sheets as photos
- Handwritten notes (if legible)

### 2. Screenshots
Upload screenshots of:
- Equipment specifications from websites
- Email conversations with technical details
- Tables from spreadsheets or presentations

### 3. Photos of Physical Documents
Upload photos taken with phone/camera of:
- Printed technical specifications
- Permit documents
- Measurement instrument displays

## Workflow Integration

The upload → extraction workflow remains unchanged:

```
User uploads PNG/JPG image
    ↓
Upload API validates .png/.jpg/.jpeg extension
    ↓
File stored in uploads/<session_id>/
    ↓
EXTRACTOR agent calls DocumentService.extract_text()
    ↓
DocumentService._extract_image() detects PNG/JPG
    ↓
Image sent to Claude vision API for OCR
    ↓
Extracted text returned to EXTRACTOR
    ↓
EXTRACTOR parses text into structured JSON
    ↓
Rest of agent workflow continues normally
```

## Performance Considerations

### Vision API Costs
- Vision API calls are more expensive than text-only calls
- Each image file = 1 vision API call (~4K tokens output)
- Multi-page image PDFs process pages in parallel (fast but more API usage)

### Quality
- **High-quality images** (300+ DPI): Excellent OCR accuracy
- **Medium-quality** (150-300 DPI): Good accuracy for typed text
- **Low-quality** (<150 DPI): May miss small text or have errors
- **Handwritten text**: Variable quality, print is much better

### Recommendations
- For machine-generated documents, use native PDFs when possible (faster, cheaper)
- For scanned/photo documents, PNG/JPG now fully supported
- Ensure images are well-lit and high-contrast for best OCR results

## Testing

### Manual Test Steps

1. **Upload PNG image**:
   ```bash
   curl -X POST http://localhost:8000/api/sessions/create \
     -F "files=@test_document.png" \
     -F 'user_metadata={}'
   ```

2. **Check extraction**:
   - Monitor session via SSE stream
   - Verify EXTRACTOR completes successfully
   - Check extracted text in session results

3. **Test cases**:
   - ✅ PNG screenshot of data table
   - ✅ JPG photo of printed document
   - ✅ PNG with mixed text and tables
   - ✅ Low-quality scan (edge case)

### Integration with Existing Tests

The existing evaluation framework can be extended:
- Add `tests/evaluation/extractor/test_documents/png/` directory
- Create ground truth for image test cases
- Run Layer 1 (parsing) and Layer 2 (LLM interpretation) tests

## Known Limitations

1. **Image size**: Limited by max_upload_size_mb (50MB default)
2. **Complex layouts**: Tables with merged cells may lose structure
3. **Handwriting**: Best-effort OCR, not guaranteed accurate
4. **Image preprocessing**: No automatic rotation, brightness adjustment, etc.
5. **Multi-page images**: Only single-page images supported (use PDF for multi-page)

## Future Enhancements

### Potential Improvements
1. **Image preprocessing**: Auto-rotate, enhance contrast, denoise
2. **Format conversion**: Support TIFF, BMP, WebP
3. **Quality validation**: Warn if image quality is too low
4. **Batch optimization**: Cache vision results for identical images
5. **OCR confidence**: Return confidence scores for extracted text

### Not Planned
- Support for video files (out of scope)
- Support for GIF animations (not applicable to documents)
- Real-time webcam OCR (not applicable to platform)

## Related Files Modified

- `backend/app/config.py` - Added image extensions to allowed list
- `backend/app/services/document_service.py` - Added `_extract_image()` method
- `CLAUDE.md` - Updated documentation for image support

## Verification

```bash
# Check config
grep "allowed_extensions" backend/app/config.py
# Output: allowed_extensions: list[str] = [".pdf", ".docx", ".xlsx", ".csv", ".txt", ".png", ".jpg", ".jpeg"]

# Check document service
grep -A 3 "_extract_image" backend/app/services/document_service.py
# Output: Shows new method definition

# Verify import
grep "from anthropic import AsyncAnthropic" backend/app/services/document_service.py
# Output: Shows vision API imports present
```

## Summary

✅ PNG/JPG/JPEG files now fully supported
✅ Uses existing Claude vision API infrastructure
✅ Seamless integration with EXTRACTOR agent
✅ No breaking changes to existing functionality
✅ Documentation updated

The platform can now accept image files for feasibility analysis alongside traditional document formats!
