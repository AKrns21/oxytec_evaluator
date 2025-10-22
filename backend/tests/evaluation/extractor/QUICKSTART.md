# Quick Start: Testing Your Excel Files

You have two Excel files ready to test:
- `20250926_Messdaten_condensed.xlsx`
- `UHU_VOC_Konz_Daten.xlsx`

## Step 1: Activate Environment

```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
```

## Step 2: Generate Ground Truth Files

Run the helper script to automatically create ground truth files:

```bash
python tests/extractor_evaluation/create_ground_truth_from_xlsx.py
```

This will:
1. Extract text from each Excel file (Layer 1)
2. Run the EXTRACTOR on each file (Layer 2)
3. Create ground truth files:
   - `test_documents/ground_truth/text/case_001_*.txt`
   - `test_documents/ground_truth/json/case_001_*.json`

## Step 3: Review Generated Ground Truth

The script shows you what was extracted. Review the files to ensure they're correct:

```bash
# View the extracted text
cat tests/extractor_evaluation/test_documents/ground_truth/text/case_001_20250926_Messdaten_condensed_expected_text.txt

# View the expected JSON
cat tests/extractor_evaluation/test_documents/ground_truth/json/case_001_20250926_Messdaten_condensed_expected.json
```

**Important**: Edit these files if needed! The automatically generated files might need adjustments:
- Fix any incorrect interpretations
- Add acceptable variations
- Adjust difficulty level
- Improve descriptions

## Step 4: Run the Tests

### Test Layer 1 Only (Document Parsing)

```bash
pytest tests/extractor_evaluation/layer1_document_parsing/test_xlsx_parsing.py -v
```

This tests if the Excel files are being read correctly by DocumentService.

### Test Layer 2 Only (LLM Interpretation)

```bash
pytest tests/extractor_evaluation/layer2_llm_interpretation/ -v
```

This tests if the LLM is correctly interpreting text (using synthetic test documents).

### Test Full Pipeline with Diagnostics

```bash
pytest tests/extractor_evaluation/test_diagnostic.py -v
```

This runs the full pipeline on your Excel files and tells you:
- Layer 1 quality (Excel parsing)
- Layer 2 quality (LLM extraction)
- **Where errors are occurring** (parsing vs. LLM)

## Step 5: Interpret Results

You'll see output like:

```
======================================================================
DIAGNOSTIC REPORT: 20250926_Messdaten_condensed.xlsx
======================================================================
Layer 1 (Excel Parsing) Quality: 96.5%
  - Text Similarity: 97.2%
  - Encoding Quality: 100%
  - Completeness: 96.0%

Layer 2 (LLM Interpretation) Quality: 91.8%
  - Critical Field Accuracy: 95.5%
  - Unit Parsing: 93.3%
  - Value Parsing: 90.0%
  - Structure Mapping: 92.1%

Error Attribution:
  - Parsing Errors: 2        ← DocumentService issues
  - LLM Errors: 5            ← EXTRACTOR prompt issues
  - Compound Errors: 1

🔧 RECOMMENDATION: Focus on improving LLM prompt engineering
======================================================================
```

**Action Based on Results**:

- **More Parsing Errors**: Improve DocumentService Excel extraction
  - Check table structure preservation
  - Fix merged cell handling
  - Improve formula evaluation

- **More LLM Errors**: Improve EXTRACTOR prompts
  - Fix unit normalization instructions
  - Improve decimal format handling
  - Better field mapping guidance

## Quick Test: Single File

To test just one file quickly:

```bash
cd backend
python -c "
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '.')

from app.services.document_service import DocumentService
from app.agents.nodes.extractor import extractor_node

async def test():
    # Extract text
    doc_service = DocumentService()
    text = await doc_service.extract_text(
        'tests/extractor_evaluation/test_documents/xlsx/20250926_Messdaten_condensed.xlsx',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

    print('EXTRACTED TEXT (first 1000 chars):')
    print('='*70)
    print(text[:1000])
    print('='*70)

    # Run extractor
    result = await extractor_node({
        'session_id': 'test',
        'documents': [{
            'filename': '20250926_Messdaten_condensed.xlsx',
            'file_path': 'tests/extractor_evaluation/test_documents/xlsx/20250926_Messdaten_condensed.xlsx',
            'mime_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }]
    })

    print('\nEXTRACTED FACTS:')
    print('='*70)
    import json
    print(json.dumps(result['extracted_facts'], indent=2)[:2000])
    print('='*70)

asyncio.run(test())
"
```

## Common Issues

### Issue: No module named 'fitz' or 'openpyxl'

**Solution**: Install dependencies:
```bash
cd backend
pip install -r requirements.txt
# or
uv pip install -r pyproject.toml
```

### Issue: Test files don't exist

**Solution**: The tests look for ground truth files. You must run Step 2 first to generate them.

### Issue: Tests are skipped

**Reason**: Ground truth files are missing. This is expected - the tests skip gracefully when files don't exist.

**Solution**:
1. Run `create_ground_truth_from_xlsx.py` to generate ground truth files
2. OR manually create them following the examples

### Issue: Layer 1 similarity is low (<90%)

**Possible causes**:
- Complex Excel table structure
- Merged cells not handled properly
- Multiple sheets with different formats

**Solution**: Check the extracted text and see what's missing or garbled.

## What to Look For

### Good Layer 1 Extraction (Excel → Text)

```
✓ All numeric values present
✓ Units preserved (m3/h, mg/Nm3, etc.)
✓ Table structure maintained
✓ No encoding issues (no Â°, Ã¼, etc.)
✓ All sheet contents extracted
```

### Good Layer 2 Extraction (Text → JSON)

```
✓ Units normalized (m³/h → m3/h, °C → degC)
✓ Decimal formats handled (850,5 → 850.5)
✓ Values mapped to correct JSON fields
✓ All pollutants extracted with CAS numbers
✓ Process parameters in right locations
```

## Next Steps After Testing

1. **If quality is good (>90%)**: Add more test cases with edge cases
2. **If Layer 1 issues**: Fix DocumentService Excel extraction
3. **If Layer 2 issues**: Update EXTRACTOR prompts in `app/agents/nodes/extractor.py`
4. **Document findings**: Note which types of Excel files cause issues

## Getting Help

- See `README.md` for full documentation
- Check `EXTRACTOR_EVALUATION_STRATEGY_V2.md` for detailed methodology
- Review test files in `layer1_document_parsing/` and `layer2_llm_interpretation/` for examples
