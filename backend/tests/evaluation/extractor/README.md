# EXTRACTOR Evaluation Test Suite

## Overview

This test suite evaluates the EXTRACTOR agent's quality using a **two-layer approach**:

1. **Layer 1: Document Parsing Quality** - Tests how well DocumentService extracts text from files
2. **Layer 2: LLM Interpretation Quality** - Tests how well the LLM interprets text into structured JSON

By testing both layers independently, we can diagnose where errors occur and target improvements effectively.

## Key Innovation

**Problem**: When the EXTRACTOR makes an error, is it because:
- The document parser extracted garbled text? (Layer 1 error)
- The LLM misinterpreted correct text? (Layer 2 error)

**Solution**: This test suite evaluates both layers separately and provides error attribution.

## Directory Structure

```
extractor_evaluation/
├── README.md                          # This file
├── conftest.py                        # Pytest fixtures
├── thresholds.py                      # Quality thresholds
│
├── layer1_document_parsing/           # Layer 1 tests
│   ├── test_pdf_parsing.py           # PDF extraction quality
│   ├── test_xlsx_parsing.py          # Excel extraction quality
│   ├── test_docx_parsing.py          # Word extraction quality (TBD)
│   └── test_csv_parsing.py           # CSV extraction quality (TBD)
│
├── layer2_llm_interpretation/         # Layer 2 tests
│   ├── test_unit_parsing.py          # Unit normalization tests
│   ├── test_value_parsing.py         # Numeric parsing tests
│   └── test_structure_mapping.py     # JSON field mapping tests (TBD)
│
├── test_diagnostic.py                 # End-to-end diagnostic tests
│
├── utils/                             # Utility modules
│   ├── validators.py                  # Schema and format validators
│   ├── comparators.py                 # Comparison utilities
│   ├── text_comparators.py           # Text comparison for Layer 1
│   └── metrics.py                     # Scoring and reporting
│
└── test_documents/                    # Test data
    ├── ground_truth/
    │   ├── text/                      # Expected extracted text (Layer 1)
    │   └── json/                      # Expected final JSON (Layer 2)
    ├── pdf/
    ├── docx/
    ├── xlsx/
    └── csv/
```

## Running Tests

### Run All Tests

```bash
cd backend
pytest tests/extractor_evaluation/ -v
```

### Run by Layer

```bash
# Layer 1 only (document parsing)
pytest tests/extractor_evaluation/layer1_document_parsing/ -v

# Layer 2 only (LLM interpretation)
pytest tests/extractor_evaluation/layer2_llm_interpretation/ -v

# Integration tests with diagnostics
pytest tests/extractor_evaluation/test_diagnostic.py -v
```

### Run by Format

```bash
# PDF tests only
pytest tests/extractor_evaluation/ -m pdf -v

# Excel tests only
pytest tests/extractor_evaluation/ -m xlsx -v
```

### Run by Error Type

```bash
# Unit parsing tests
pytest tests/extractor_evaluation/ -m unit_parsing -v

# Value parsing tests
pytest tests/extractor_evaluation/ -m value_parsing -v

# Structure mapping tests
pytest tests/extractor_evaluation/ -m structure_mapping -v
```

### Run with Coverage

```bash
pytest tests/extractor_evaluation/ --cov=app.agents.nodes.extractor --cov=app.services.document_service -v
```

### Skip Slow Tests (OCR/Vision)

```bash
pytest tests/extractor_evaluation/ -v -m "not slow"
```

## Creating Test Cases

### Step 1: Create Test Document

Place your test document in the appropriate directory:
- `test_documents/pdf/case_XXX.pdf`
- `test_documents/xlsx/case_XXX.xlsx`
- etc.

### Step 2: Create Ground Truth Text (Layer 1)

Extract what the text **should** look like after document parsing:

**File**: `test_documents/ground_truth/text/case_XXX_expected_text.txt`

```
--- Page 1 ---
VOC Measurement Report

Exhaust Air Parameters:
Flow rate: 5000 m3/h
Temperature: 45 degC
Pressure: -5 mbar

Pollutant Analysis:
| Substance      | CAS Number | Concentration | Unit    |
|----------------|------------|---------------|---------|
| Toluene        | 108-88-3   | 850.5         | mg/Nm3  |
| Ethyl acetate  | 141-78-6   | 420.0         | mg/Nm3  |

Total VOC: 1270.5 mg/Nm3
```

**Key Points**:
- Preserve original numeric formats (850.5 or 850,5)
- Keep unit notation as written (m³/h or m3/h)
- Maintain table structure
- Include page markers for PDFs

### Step 3: Create Ground Truth JSON (Layer 2)

Define what the final extraction **should** produce:

**File**: `test_documents/ground_truth/json/case_XXX_expected.json`

```json
{
  "test_case_id": "case_001",
  "description": "Standard VOC measurement report",
  "difficulty": "easy",
  "focus_areas": ["unit_parsing", "pollutant_extraction"],
  "expected_extraction": {
    "pollutant_characterization": {
      "pollutant_list": [
        {
          "name": "Toluene",
          "cas_number": "108-88-3",
          "concentration": 850.5,
          "concentration_unit": "mg/Nm3",
          "category": "VOC"
        },
        {
          "name": "Ethyl acetate",
          "cas_number": "141-78-6",
          "concentration": 420.0,
          "concentration_unit": "mg/Nm3",
          "category": "VOC"
        }
      ],
      "total_load": {
        "tvoc": 1270.5,
        "tvoc_unit": "mg/Nm3",
        "total_carbon": null,
        "odor_units": null
      },
      "measurement_tables": ""
    },
    "process_parameters": {
      "flow_rate": {
        "value": 5000,
        "unit": "m3/h",
        "min_value": null,
        "max_value": null
      },
      "temperature": {
        "value": 45,
        "unit": "degC"
      },
      "pressure": {
        "value": -5,
        "unit": "mbar",
        "type": "negative"
      },
      "humidity": {
        "value": null,
        "unit": null,
        "type": null
      },
      "oxygen_content_percent": null,
      "particulate_load": {
        "value": null,
        "unit": null
      },
      "operating_schedule": null
    }
    // ... rest of schema
  },
  "critical_fields": [
    "pollutant_characterization.pollutant_list[0].concentration",
    "pollutant_characterization.pollutant_list[0].concentration_unit",
    "process_parameters.flow_rate.value",
    "process_parameters.flow_rate.unit"
  ],
  "acceptable_variations": {
    "pollutant_characterization.pollutant_list[0].cas_number": [
      "108-88-3",
      "108883",
      null
    ]
  }
}
```

**Key Sections**:
- `expected_extraction`: The full JSON structure the LLM should produce
- `critical_fields`: Fields that MUST be correct (100% accuracy required)
- `acceptable_variations`: Alternative values that are acceptable (e.g., CAS number formats)

### Step 4: Write Test

Add a test case to the appropriate test file:

```python
@pytest.mark.asyncio
async def test_case_XXX(self, extract_text_only, run_extractor, test_documents_dir, load_expected_text, load_expected_json):
    """Test description."""
    doc_path = test_documents_dir / "pdf" / "case_XXX.pdf"

    # Layer 1 check
    extracted_text = await extract_text_only(doc_path)
    expected_text = load_expected_text("case_XXX_expected_text.txt")
    comparison = compare_extracted_text(extracted_text, expected_text)
    assert comparison.similarity_score > 0.95

    # Layer 2 check
    extracted_facts = await run_extractor(doc_path)
    expected_data = load_expected_json("case_XXX_expected.json")
    # ... assertions
```

## Understanding Test Results

### Layer 1 Results

```
Layer 1 (Document Parsing) Quality: 95.5%
  - Text Similarity: 96.2%
  - Encoding Quality: 100%
  - Completeness: 95.0%
```

**Interpretation**:
- **Text Similarity**: How similar is extracted text to expected (Levenshtein distance)
- **Encoding Quality**: Are there encoding artifacts (Â°, Ã¼, etc.)?
- **Completeness**: Is all expected content present?

### Layer 2 Results

```
Layer 2 (LLM Interpretation) Quality: 92.3%
  - Critical Field Accuracy: 100%
  - Unit Parsing: 95.0%
  - Value Parsing: 94.5%
  - Structure Mapping: 89.0%
```

**Interpretation**:
- **Overall Accuracy**: Percentage of fields correctly extracted
- **Critical Field Accuracy**: Accuracy for high-priority fields only
- **Unit Parsing**: Correct normalization of units (m³/h → m3/h)
- **Value Parsing**: Correct interpretation of numbers (850,5 → 850.5)
- **Structure Mapping**: Correct JSON field assignment

### Error Attribution

```
Error Attribution:
  - Document Parsing Errors: 2
  - LLM Interpretation Errors: 5
  - Compound Errors: 1
```

**Interpretation**:
- **Parsing Errors**: Errors caused by DocumentService (fix document extraction)
- **LLM Errors**: Errors caused by LLM (fix prompts or model)
- **Compound Errors**: Errors from both layers (fix both)

**Actionable Insight**: If LLM errors > parsing errors, focus on prompt engineering. If parsing errors > LLM errors, focus on document extraction.

## Quality Thresholds

Thresholds are defined in `thresholds.py`:

### Layer 1 Thresholds

| Format | Text Similarity | Encoding Quality | Completeness |
|--------|----------------|------------------|--------------|
| PDF (text-based) | 95% | 100% | 95% |
| PDF (scanned) | 85% | 90% | 80% |
| Excel | 90% | 100% | 92% |
| Word | 93% | 100% | 93% |
| CSV | 98% | 100% | 98% |

### Layer 2 Thresholds

| Difficulty | Overall | Critical Fields | Unit | Value | Structure |
|------------|---------|----------------|------|-------|-----------|
| Easy | 95% | 100% | 98% | 98% | 95% |
| Medium | 90% | 95% | 92% | 92% | 90% |
| Hard | 85% | 90% | 85% | 85% | 85% |
| Very Hard | 80% | 85% | 80% | 80% | 80% |

## Common Issues and Solutions

### Issue: Text similarity low for PDFs

**Symptoms**: Layer 1 text similarity < 90%

**Possible Causes**:
1. Scanned PDF without OCR
2. Complex table layout
3. Rotated pages

**Solutions**:
1. Enable vision API fallback (check `document_service.py`)
2. Improve table extraction logic
3. Add page rotation detection

### Issue: Unit parsing accuracy low

**Symptoms**: Layer 2 unit parsing < 90%

**Possible Causes**:
1. LLM not following normalization instructions
2. Ambiguous unit notation in prompt

**Solutions**:
1. Review EXTRACTOR prompt in `extractor.py:61-477`
2. Add more explicit examples of unit normalization
3. Check if LLM is using JSON mode correctly

### Issue: Value parsing errors (decimal separators)

**Symptoms**: Layer 2 value parsing < 90%, errors like 850,5 → 8505

**Possible Causes**:
1. LLM not handling European decimal format
2. Context clues about locale missing

**Solutions**:
1. Add explicit handling in prompt: "850,5 means 850.5 (European format)"
2. Provide more examples in prompt
3. Check if document mentions locale/region

### Issue: Structure mapping errors

**Symptoms**: Data in wrong JSON fields

**Possible Causes**:
1. Ambiguous data (e.g., multiple flow rates)
2. Unclear field descriptions in prompt

**Solutions**:
1. Add more context in prompt about which data goes where
2. Use explicit field mapping examples
3. Add validation in extractor node

## CI/CD Integration

### GitHub Actions Example

```yaml
name: EXTRACTOR Quality Check

on:
  push:
    paths:
      - 'backend/app/agents/nodes/extractor.py'
      - 'backend/app/services/document_service.py'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run EXTRACTOR evaluation
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cd backend
          pytest tests/extractor_evaluation/ -v --cov=app.agents.nodes.extractor
      - name: Check thresholds
        run: |
          python backend/tests/extractor_evaluation/check_thresholds.py
```

## Best Practices

1. **Start with Easy Cases**: Create simple test documents first to establish baseline
2. **Test Both Layers**: Always create both text and JSON ground truth
3. **Document Edge Cases**: When you find a bug, create a test case for it
4. **Use Markers**: Tag tests appropriately (`@pytest.mark.layer1`, `@pytest.mark.pdf`, etc.)
5. **Keep Ground Truth Updated**: When you improve extraction, update ground truth files
6. **Review Failed Tests**: Use diagnostic tests to understand *why* tests fail

## Contributing

When adding new tests:
1. Follow naming convention: `case_XXX_descriptive_name.{pdf|xlsx|docx|csv}`
2. Create both text and JSON ground truth
3. Mark difficulty level in JSON ground truth
4. Add test docstring explaining what is being tested
5. Use appropriate pytest markers

## Troubleshooting

### Tests are skipped

**Cause**: Test document doesn't exist yet

**Solution**: Create the test document or remove the test

### Encoding issues detected

**Cause**: DocumentService is producing garbled text

**Solution**: Check encoding handling in `document_service.py`

### LLM not normalizing units

**Cause**: Prompt may not be explicit enough

**Solution**: Review and update prompt in `extractor.py`

## Future Enhancements

- [ ] Add multi-language support (German, English, French)
- [ ] Create visual diff tool for comparing extracted vs. expected
- [ ] Add performance benchmarks (extraction time per document)
- [ ] Create automated ground truth generation tool
- [ ] Add fuzzy matching for minor text variations
- [ ] Implement active learning to identify uncertain extractions

## Contact

For questions or issues with the evaluation suite, refer to the main project documentation or create an issue in the repository.
