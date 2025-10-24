# EXTRACTOR Testing Strategy: Page-Level vs Document-Level Extraction

**Date:** 2025-10-24
**Status:** Analysis Complete - Recommendations Approved
**Context:** Pre-Phase 2 planning for EXTRACTOR v2.0.0 implementation

---

## Executive Summary

**Question Asked:** Should we split Bericht.pdf (13 pages) into individual pages and extract content simultaneously, then store in a vector database for PLANNER access?

**Answer:** **NO** - Continue with single-document extraction approach, store as JSON

**Rationale:**
1. Page-level extraction conflicts with EXTRACTOR v2.0.0 architecture goals
2. Creates data quality issues (context loss, fragmentation)
3. Vector store is wrong abstraction for structured extracted_facts
4. Current approach already optimal for the multi-agent workflow

---

## Analysis

### Current Architecture (EXTRACTOR v1.0.0)

**Flow:**
```
PDF Document (13 pages)
  ↓
DocumentService._extract_pdf()
  ├─ Sequential page extraction with markers
  ├─ Vision API fallback for image-based PDFs (parallel processing)
  └─ Returns: "--- Page 1 ---\n{text}\n\n--- Page 2 ---\n{text}..."
  ↓
EXTRACTOR Node (extractor.py:105-224)
  ├─ Combines all document texts
  ├─ Single LLM call with complete context
  └─ Returns: extracted_facts JSON
  ↓
PLANNER receives complete structured facts
```

**Key Files:**
- `backend/app/services/document_service.py:56-118` - PDF extraction with vision fallback
- `backend/app/agents/nodes/extractor.py:105-224` - EXTRACTOR node with single-pass extraction
- `backend/app/agents/prompts/versions/extractor_v1_0_0.py` - Current prompt

### Proposed Alternative (Rejected)

**What was considered:**
```
PDF Document (13 pages)
  ↓
Split into 13 separate pages
  ↓
Parallel EXTRACTOR calls (13x)
  ├─ Page 1 → extracted_facts_1.json
  ├─ Page 2 → extracted_facts_2.json
  └─ Page 13 → extracted_facts_13.json
  ↓
Merge strategy (???)
  └─ Combine pollutant_list arrays
  └─ Resolve conflicts
  └─ Deduplicate extraction_notes
  ↓
Option A: Store merged JSON
Option B: Store in vector database
  ├─ Generate embeddings for each page
  ├─ Store in pgvector
  └─ PLANNER queries via similarity search
```

**Why Rejected:**

#### Problem 1: Architecture Mismatch

**EXTRACTOR v2.0.0 Design Goals (from refactoring instructions):**
- ✅ Pure technical extraction (no business logic)
- ✅ Single consolidated output: `extracted_facts.json`
- ✅ Flag missing data via `extraction_notes[]`
- ✅ SIMPLIFY the EXTRACTOR prompt (50% size reduction)

**Page-level extraction conflicts:**
- ❌ Requires complex merging logic (new business logic!)
- ❌ Produces 13 separate outputs (not consolidated)
- ❌ Duplicates extraction_notes need deduplication rules
- ❌ ADDS complexity (opposite of goal)

#### Problem 2: Data Quality Degradation

**Context Loss Examples:**

**Example 1: Cross-page references**
```
Page 2:
  "Pollutant: Toluene"
  "CAS Number: 108-88-3"

Page 3:
  "Concentration: 850 mg/Nm3"
  "Temperature: 45°C"
```

**Single-document extraction (current):**
→ Correctly links: `{"name": "Toluene", "cas_number": "108-88-3", "concentration": 850, "unit": "mg/Nm3"}`

**Page-level extraction:**
→ Page 2: `{"name": "Toluene", "cas_number": "108-88-3", "concentration": null}`
→ Page 3: `{"concentration": 850, "unit": "mg/Nm3"}` ← Missing pollutant name!
→ Merging strategy: How do we know these belong together?

**Example 2: Multi-page tables**
```
Page 5:
  Table Header: | Substance | CAS | Concentration |
  Row 1: Toluene | 108-88-3 | 850 mg/Nm3

Page 6:
  Row 2: Ethyl acetate | 141-78-6 | 420 mg/Nm3
  Row 3: Methanol | 67-56-1 | 150 mg/Nm3
```

**Single-document extraction:**
→ All 3 pollutants extracted correctly from complete table

**Page-level extraction:**
→ Page 5 gets headers + row 1
→ Page 6 gets rows 2-3 WITHOUT headers
→ EXTRACTOR on page 6 doesn't know what "850" refers to

**Example 3: Section references**
```
Page 4:
  "Process temperature: See Section 3.2 for details"

Page 7 (Section 3.2):
  "Operating temperature: 45-60°C"
```

**Single-document extraction:**
→ LLM can follow reference, extract 45-60°C correctly

**Page-level extraction:**
→ Page 4 extraction: `{"temperature": {"value": null}}` + extraction_note: "Refers to Section 3.2"
→ Page 7 extraction: `{"temperature": {"value": "45-60°C"}}` ← No context that this is the referenced value
→ Merging: How do we know to use page 7's value for page 4's field?

#### Problem 3: Merging Complexity

**Challenge 1: Deduplication**
```json
// Page 2 extraction
{
  "pollutant_list": [
    {"name": "Toluene", "cas_number": "108-88-3", "concentration": null}
  ]
}

// Page 3 extraction
{
  "pollutant_list": [
    {"name": "Toluene", "cas_number": "108-88-3", "concentration": 850, "unit": "mg/Nm3"}
  ]
}

// How to merge?
// Option A: Keep both → Duplicate entry
// Option B: Merge by name → Need smart merge logic (null values should be overridden)
// Option C: Merge by CAS → What if CAS is null on one page?
```

**Challenge 2: Conflict Resolution**
```json
// Page 5 extraction
{
  "process_parameters": {
    "temperature": {"value": 45, "unit": "degC"}
  }
}

// Page 7 extraction
{
  "process_parameters": {
    "temperature": {"value": 60, "unit": "degC"}
  }
}

// How to resolve?
// Option A: Take first value → Might be wrong
// Option B: Take last value → Might be wrong
// Option C: Average → Nonsensical for setpoint values
// Option D: Store both with extraction_note → Which one does PLANNER use?
```

**Challenge 3: extraction_notes Deduplication**
```json
// 5 pages mention "Oxygen content not provided"
// Do we create 5 identical extraction_notes?
// Or deduplicate and lose per-page context?
```

**Implementation Cost:**
- 200-300 lines of merge logic
- Unit tests for all merge scenarios
- Error handling for conflicts
- Documentation for merge rules
- Maintenance burden

#### Problem 4: Performance

**Current Approach:**
```
DocumentService: 500ms (13 pages)
EXTRACTOR (1 LLM call): 5-10s
Total: ~6-10s
```

**Page-level Approach:**
```
DocumentService: 500ms (13 pages)
13x EXTRACTOR calls in parallel: 5-10s (same - API rate limits)
Merge logic: 500ms
Total: ~6-11s (no improvement!)
```

**Why no speedup?**
- LLM API is the bottleneck (not PDF parsing)
- Parallel LLM calls hit rate limits
- Even if no rate limits: 13 small calls ≈ 1 large call (token processing time)
- Added merge overhead

**Token Cost:**
- Current: 1 call × (prompt + 13 pages) = ~15k tokens
- Page-level: 13 calls × (prompt + 1 page) = 13 × ~3k tokens = ~39k tokens
- **Cost increase: 2.6x!**

#### Problem 5: Vector Store Mismatch

**What Vector Stores Are Good For:**
- Unstructured text search (e.g., "Find all mentions of safety concerns")
- Semantic similarity (e.g., "Find sections similar to: equipment maintenance")
- Large document collections (e.g., 100+ PDFs)
- Exploratory queries (e.g., "What does the customer say about X?")

**What EXTRACTOR Produces:**
- Structured data: `extracted_facts.json`
- Schema-validated fields: `pollutant_list[]`, `process_parameters{}`
- Typed values: `temperature.value: float`, `cas_number: string`

**PLANNER Access Pattern (from refactoring instructions):**
```python
# PLANNER Phase 1: Enrichment
for pollutant in extracted_facts["pollutant_characterization"]["pollutant_list"]:
    if pollutant["cas_number"] is None:
        # Look up CAS via web_search
        pollutant["cas_number"] = await web_search(f"{pollutant['name']} CAS number")

# Direct dictionary access - NO SEARCH NEEDED!
```

**PLANNER Phase 2: Conditional Subagent Creation**
```python
# Check if carcinogen subagent needed
carcinogen_substances = [
    p for p in enriched_facts["pollutant_characterization"]["pollutant_list"]
    if p.get("carcinogen_group") in ["1", "2A"]
]

if len(carcinogen_substances) > 0:
    create_subagent("Carcinogen Risk Assessment Specialist")

# Direct field access - NO SEARCH NEEDED!
```

**SUBAGENT Access Pattern:**
```python
# VOC Chemie Specialist receives enriched_facts
voc_list = enriched_facts["pollutant_characterization"]["pollutant_list"]

for voc in voc_list:
    if voc["concentration"] > 500:  # mg/Nm3
        findings.append({
            "substance": voc["name"],
            "risk": "High concentration requires oxidizer"
        })

# Direct iteration - NO SEARCH NEEDED!
```

**Vector Store Would Require:**
```python
# WRONG approach - adds unnecessary complexity
query = "Find temperature values"
results = await vector_store.similarity_search(query, k=5)
temperature = extract_from_results(results)  # Parsing unstructured results

# vs

# RIGHT approach - direct access
temperature = extracted_facts["process_parameters"]["temperature"]["value"]
```

**When Vector Store WOULD Make Sense:**
```
Scenario: 100-page PDF with narrative text
"Customer inquiry: We manufacture automotive paints and have concerns about
VOC regulations in Bavaria. Our current process uses toluene and xylene.
We've heard about new ATEX requirements but aren't sure if they apply to us.
What are your recommendations?"

→ PLANNER needs to search for:
  - "What VOCs are mentioned?" → Similarity search for chemical names
  - "What regulations are mentioned?" → Search for legal references
  - "What are customer concerns?" → Search for question patterns

→ This is RAG-based extraction, not the current structured approach
```

### Recommended Architecture (Approved)

**Keep Current Single-Document Approach:**

```
PDF Document (13 pages)
  ↓
DocumentService._extract_pdf()
  └─ Returns: "--- Page 1 ---\n{text}\n\n--- Page 2 ---\n{text}..." (single string)
  ↓
EXTRACTOR v2.0.0 Node
  ├─ Single LLM call with complete document context
  ├─ Prompt includes extraction_notes instructions
  └─ Returns: {extracted_facts: {...}, extraction_notes: [...]}
  ↓
Store in PostgreSQL (existing tables)
  └─ agent_outputs.content: JSONB with extracted_facts
  ↓
PLANNER receives complete extracted_facts via state
  ├─ Phase 1: Enrichment (add CAS numbers, normalize units)
  └─ Phase 2: Create subagents (conditional logic based on facts)
```

**Why This Works:**

1. **Maintains Context:** LLM sees entire document, can link cross-references
2. **Simplicity:** No merge logic, no conflict resolution
3. **Performance:** Optimal token usage, fastest extraction
4. **Schema Validation:** Single JSON object validates against schema
5. **Direct Access:** PLANNER/SUBAGENTS use dictionary access (fastest)

---

## Implementation Plan (Phase 2)

### Week 1: EXTRACTOR v2.0.0 Implementation

**Task 1: Create New Prompt Version**

File: `backend/app/agents/prompts/versions/extractor_v2_0_0.py`

**Changes:**
1. Remove carcinogen detection (lines 47-94 from v1.0.0)
2. Remove severity ratings from data_quality_issues
3. Add extraction_notes system:
   ```python
   EXTRACTION_NOTES_INSTRUCTIONS = """
   When you encounter missing, unclear, or ambiguous data, add to extraction_notes:

   {
     "extraction_notes": [
       {
         "field": "pollutant_list[0].cas_number",
         "status": "missing_in_source",
         "note": "Toluene mentioned without CAS number"
       }
     ]
   }

   Status types:
   - not_provided_in_documents: Field not mentioned
   - missing_in_source: Mentioned but incomplete
   - unclear_format: Present but ambiguous
   - table_empty: Table structure exists but empty cells
   - extraction_uncertain: Unsure of interpretation
   """
   ```

4. Add technical cleanup rules:
   ```python
   TECHNICAL_CLEANUP_RULES = """
   MUST perform these normalizations:

   1. Units: "m³/h" → "m3/h", "°C" → "degC"
   2. Numbers: "1.200" (German) → 1200
   3. VOC names: "Ethylacetat" → "Ethyl acetate" (if unambiguous)
   4. CAS format: "108-88-3" (preserve dashes)
   """
   ```

5. Update JSON schema to include extraction_notes

**Task 2: Update EXTRACTOR Node**

File: `backend/app/agents/nodes/extractor.py`

**Changes:**
- Line 153: Update to use `settings.extractor_prompt_version = "v2.0.0"`
- Line 183: Add validation for extraction_notes field
- No changes to document processing flow (keep single-document approach)

**Task 3: Update Config**

File: `backend/app/config.py`

```python
# EXTRACTOR configuration
extractor_prompt_version: str = "v2.0.0"  # Updated from v1.0.0
extractor_model: str = "gpt-5"
extractor_temperature: float = 0.2
```

### Week 1: Testing Strategy

**Test 1: Adapt Layer 1 Tests (Document Parsing)**

File: `backend/tests/evaluation/extractor/layer1_document_parsing/test_pdf_parsing.py`

**Add new test:**
```python
@pytest.mark.asyncio
async def test_bericht_pdf_extraction(extract_text_only, test_documents_dir):
    """Test extraction from 13-page Bericht.pdf."""
    doc_path = test_documents_dir / "pdf" / "Bericht.pdf"

    extracted_text = await extract_text_only(doc_path)

    # Should contain all 13 pages
    page_markers = extracted_text.count("--- Page")
    assert page_markers >= 13, f"Expected 13 pages, found {page_markers}"

    # Should preserve table structure (check for known table content)
    assert "Toluene" in extracted_text or "toluene" in extracted_text

    # Should not have encoding issues
    assert "Â" not in extracted_text
    assert len(extracted_text) > 10000  # Reasonable minimum for 13 pages
```

**Test 2: Layer 2 Tests (LLM Interpretation)**

File: `backend/tests/evaluation/extractor/layer2_llm_interpretation/test_extraction_notes.py` (NEW)

```python
"""Test extraction_notes field in EXTRACTOR v2.0.0."""

import pytest


@pytest.mark.layer2
@pytest.mark.extraction_notes
class TestExtractionNotes:
    """Test extraction_notes functionality."""

    @pytest.mark.asyncio
    async def test_missing_cas_number_flagged(
        self, run_extractor, create_synthetic_document
    ):
        """Test that missing CAS numbers are flagged in extraction_notes."""

        synthetic_text = """
        Pollutant Measurements

        Toluene: 850 mg/Nm3
        Ethyl acetate: 420 mg/m3
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_missing_cas.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        # Check extraction_notes
        extraction_notes = extracted_facts.get("extraction_notes", [])
        assert len(extraction_notes) > 0, "Expected extraction_notes for missing CAS numbers"

        # Should flag Toluene CAS missing
        toluene_notes = [
            note for note in extraction_notes
            if "toluene" in note["field"].lower() and "cas" in note["field"].lower()
        ]
        assert len(toluene_notes) > 0, "Toluene CAS number should be flagged as missing"
        assert toluene_notes[0]["status"] == "missing_in_source"

    @pytest.mark.asyncio
    async def test_unclear_unit_flagged(
        self, run_extractor, create_synthetic_document
    ):
        """Test that unclear units are flagged."""

        synthetic_text = """
        Process Parameters

        Flow rate: 5000 (unit not specified)
        Temperature: 45
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_unclear_unit.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should flag unclear flow rate unit
        flow_notes = [
            note for note in extraction_notes
            if "flow_rate" in note["field"]
        ]
        assert len(flow_notes) > 0, "Flow rate unit should be flagged as unclear"
        assert flow_notes[0]["status"] in ["unclear_format", "missing_in_source"]

    @pytest.mark.asyncio
    async def test_no_notes_for_complete_data(
        self, run_extractor, create_synthetic_document
    ):
        """Test that extraction_notes is empty when all data is complete."""

        synthetic_text = """
        Pollutant Measurements

        Toluene (CAS: 108-88-3): 850 mg/Nm3
        Flow rate: 5000 m3/h
        Temperature: 45 degC
        """

        doc_path = create_synthetic_document(synthetic_text, filename="test_complete.txt")
        extracted_facts = await run_extractor(doc_path, mime_type="text/plain")

        extraction_notes = extracted_facts.get("extraction_notes", [])

        # Should have zero or minimal notes
        assert len(extraction_notes) == 0, (
            f"Expected no extraction_notes for complete data, got: {extraction_notes}"
        )
```

**Test 3: Create Ground Truth for Bericht.pdf**

File: `backend/tests/evaluation/extractor/test_documents/ground_truth/json/bericht_expected.json`

```json
{
  "document_name": "Bericht.pdf",
  "expected_extraction": {
    "pollutant_characterization": {
      "pollutant_list": [
        {
          "name": "Toluene",
          "cas_number": "108-88-3",
          "concentration": 850,
          "concentration_unit": "mg/Nm3",
          "category": "VOC"
        }
        // ... add all expected pollutants from Bericht.pdf
      ]
    },
    "process_parameters": {
      "flow_rate": {
        "value": 5000,
        "unit": "m3/h"
      }
      // ... add all expected parameters
    },
    "extraction_notes": [
      {
        "field": "pollutant_list[2].cas_number",
        "status": "missing_in_source",
        "note": "Ethyl acetate mentioned without CAS"
      }
      // ... expected notes for known missing data
    ]
  },
  "critical_fields": [
    "pollutant_characterization.pollutant_list[*].name",
    "pollutant_characterization.pollutant_list[*].concentration",
    "process_parameters.flow_rate.value",
    "process_parameters.temperature.value"
  ]
}
```

**Test 4: Run Diagnostic Test**

```bash
cd backend
source .venv/bin/activate

# Test with v2.0.0
EXTRACTOR_PROMPT_VERSION=v2.0.0 python3 tests/evaluation/extractor/test_single_file.py Bericht.pdf

# Expected output:
# ✓ extraction_notes populated with 3-5 items
# ✓ No carcinogen flags (removed in v2.0.0)
# ✓ No severity ratings in data_quality_issues
# ✓ All pollutants extracted with proper units
```

### Week 1: A/B Comparison

**Compare v1.0.0 vs v2.0.0:**

```bash
# Run v1.0.0 test
EXTRACTOR_PROMPT_VERSION=v1.0.0 python3 tests/evaluation/extractor/test_single_file.py Bericht.pdf > v1_bericht_output.txt

# Run v2.0.0 test
EXTRACTOR_PROMPT_VERSION=v2.0.0 python3 tests/evaluation/extractor/test_single_file.py Bericht.pdf > v2_bericht_output.txt

# Compare outputs
diff v1_bericht_output.txt v2_bericht_output.txt

# Expected differences:
# - v1.0.0: Has carcinogen flags, severity ratings
# - v2.0.0: Has extraction_notes, no business logic
# - v2.0.0: 50% fewer tokens used
```

**Quality Metrics:**

| Metric | v1.0.0 Target | v2.0.0 Target | Notes |
|--------|---------------|---------------|-------|
| Extraction completeness | 95% | 95% | Should maintain quality |
| Unit normalization | 90% | 95% | Improved with cleanup rules |
| extraction_notes coverage | N/A | 80% | New field - should flag most missing data |
| Token usage | ~15k | ~7-8k | 50% reduction from prompt simplification |
| Duration | 6-10s | 6-10s | Should be similar (same LLM call) |
| Error rate | <5% | <5% | Should maintain or improve |

---

## Key Decisions Made

### Decision 1: Single-Document Extraction ✅

**Rationale:**
- Maintains semantic context across pages
- No merge logic complexity
- Optimal token usage
- Aligns with v2.0.0 simplification goals

**Alternative Rejected:** Page-level parallel extraction

### Decision 2: JSON Storage ✅

**Rationale:**
- PLANNER/SUBAGENTS use direct dictionary access
- Schema validation ensures consistency
- No search latency
- PostgreSQL JSONB is sufficient

**Alternative Rejected:** Vector database for extracted_facts

### Decision 3: Keep Existing DocumentService Flow ✅

**Rationale:**
- Already optimized (vision API parallel for image PDFs)
- Page markers preserve structure
- No changes needed for v2.0.0

**Alternative Rejected:** Modify DocumentService for page-level output

### Decision 4: Focus Testing on extraction_notes ✅

**Rationale:**
- New feature in v2.0.0
- Critical for PLANNER Phase 1 (enrichment)
- Needs validation that missing data is properly flagged

**Alternative Rejected:** Only test existing fields

---

## Lessons Learned

### Why Page-Level Seemed Appealing (But Wasn't)

**Initial Intuition:**
"Splitting into pages → parallel extraction → faster processing"

**Reality:**
- LLM API is bottleneck (not PDF parsing)
- Parallel LLM calls hit rate limits
- Context loss degrades quality
- Merge logic adds complexity

**Key Insight:** "Faster" isn't always better if it sacrifices quality and simplicity

### Why Vector Store Seemed Appealing (But Wasn't)

**Initial Intuition:**
"Vector database → semantic search → flexible PLANNER queries"

**Reality:**
- PLANNER doesn't need search (works with structured facts)
- Direct dictionary access is faster than similarity search
- Schema validation prevents field access errors
- Vector embeddings add cost + latency

**Key Insight:** Choose data structure based on access patterns, not "cool technology"

### What Actually Matters

1. **Context preservation** > Speed optimization
2. **Simplicity** > Feature richness
3. **Direct access** > Flexible search (for structured data)
4. **Schema validation** > Unstructured flexibility

---

## Next Steps

### Immediate (Week 1)

1. ✅ **Implement EXTRACTOR v2.0.0** (3-4 days)
   - Create `extractor_v2_0_0.py`
   - Update config to v2.0.0
   - Add extraction_notes validation

2. ✅ **Create Test Suite** (1-2 days)
   - Add Bericht.pdf tests
   - Create ground truth JSON
   - Write extraction_notes tests

3. ✅ **Run A/B Comparison** (0.5 days)
   - Test v1.0.0 vs v2.0.0
   - Document quality metrics
   - Update PROMPT_CHANGELOG.md

### Follow-up (Week 2)

4. **Deploy to Staging** (Week 2)
   - Update production config
   - Monitor metrics for 1 week
   - Collect engineer feedback

5. **Proceed to PLANNER v2.0.0** (Week 2)
   - Implement Phase 1 (enrichment with extraction_notes)
   - Implement Phase 2 (conditional subagent creation)

---

## References

**Refactoring Instructions:**
- `docs/architecture/agent_refactoring_instructions.md` → Section 1 (EXTRACTOR changes)

**Implementation Guide:**
- `docs/development/REFACTORING_STEP_BY_STEP_GUIDE.md` → Phase 2

**Architecture:**
- `docs/architecture/AGENT_REFACTORING_ARCHITECTURE.md` → Data flow diagrams

**Current Code:**
- `backend/app/agents/nodes/extractor.py` → EXTRACTOR node implementation
- `backend/app/services/document_service.py` → PDF extraction logic
- `backend/app/agents/prompts/versions/extractor_v1_0_0.py` → Current prompt

**Test Suite:**
- `backend/tests/evaluation/extractor/` → Existing evaluation framework
- `backend/tests/evaluation/extractor/test_single_file.py` → Diagnostic test script

---

## Conclusion

**Question:** Should we split documents into pages and extract simultaneously?

**Answer:** **NO** - Single-document extraction is optimal

**Why:**
1. ✅ Preserves context (cross-references, multi-page tables)
2. ✅ Simpler architecture (no merge logic)
3. ✅ Better token efficiency (2.6x cheaper)
4. ✅ Aligns with v2.0.0 goals (simplification)
5. ✅ Faster implementation (no new infrastructure)

**Implementation:**
- Keep existing single-document flow
- Focus on EXTRACTOR v2.0.0 improvements (extraction_notes, cleanup rules)
- Test with Bericht.pdf as comprehensive validation
- Measure quality improvement with A/B comparison

**Timeline:** Week 1 of Phase 2 (2-3 days implementation + 1-2 days testing)

---

**Document Version:** 1.0
**Last Updated:** 2025-10-24
**Author:** Claude (Code Analysis Specialist)
**Approved By:** Andreas
**Status:** Analysis Complete ✅ | Recommendations Approved ✅
