# Agent Refactoring Instructions

**Purpose:** Guidelines for refactoring the Oxytec Multi-Agent Feasibility Platform to implement content-first architecture and clear separation of concerns.

**Status:** Section 1 & 2 Complete | Section 3+ In Progress
**Last Updated:** 2025-10-24

---

## Table of Contents

1. [Overview & Motivation](#section-1-overview--motivation)
2. [EXTRACTOR Agent Refactoring](#section-2-extractor-agent-refactoring)
3. [PLANNER Agent Refactoring](#section-3-planner-agent-refactoring) (Planned)
4. [SUBAGENT Agent Refactoring](#section-4-subagent-agent-refactoring) (Planned)
5. [RISK_ASSESSOR Agent Refactoring](#section-5-risk_assessor-agent-refactoring) (Planned)
6. [WRITER Agent Refactoring](#section-6-writer-agent-refactoring) (Planned)

---

## Section 1: Overview & Motivation

### 1.1 The Problem

**User Feedback (2025-10-24):**
> "I don't see the content but rather just categories"

The original multi-agent system suffered from:

1. **Schema-First Extraction** → 40% data loss
   - EXTRACTOR forced content into predefined fields
   - Content that didn't fit categories was discarded
   - Tables were split across multiple schema fields
   - User saw structured output but missed raw content

2. **Mixed Concerns** → Prompt bloat
   - EXTRACTOR did extraction + enrichment + business logic (~6,500 tokens)
   - PLANNER did planning + data validation + risk assessment
   - SUBAGENTS had overlapping responsibilities
   - No clear ownership of data quality issues

3. **Tight Coupling** → Difficult to evolve
   - Changing EXTRACTOR schema required updating all downstream agents
   - Adding new document types meant modifying multiple prompts
   - Testing was difficult due to interconnected logic

### 1.2 The Solution: Content-First Architecture

**New Philosophy:**
```
Document → EXTRACTOR (preserve 100%) → PLANNER (interpret) → SUBAGENTS (analyze) → WRITER (synthesize)
```

**Key Principles:**

1. **Preservation Over Interpretation**
   - EXTRACTOR preserves ALL content in `pages[]` structure
   - Add light categorization hints (interpretation_hint, content_categories)
   - No forcing content into predefined schemas

2. **Single Responsibility**
   - EXTRACTOR: Technical extraction only
   - PLANNER: Interpret content → Create subagent tasks
   - SUBAGENTS: Focused analysis (one concern per agent)
   - RISK_ASSESSOR: Synthesize findings
   - WRITER: Generate report

3. **Loose Coupling**
   - Agents communicate via state dict
   - Schema changes don't cascade
   - Each agent can evolve independently

### 1.3 Refactoring Strategy

**Phase 1: EXTRACTOR v3.0.0** ✅ COMPLETE
- Implement content-first extraction
- Preserve 100% of document content in `pages[]`
- Add `interpretation_hint` for tables
- Add `quick_facts` for fast access
- **Status:** Tested & Validated (2025-10-24)

**Phase 2: PLANNER v2.1.0** 🔧 IN PROGRESS
- Consume `pages[]` format
- Interpret content using `interpretation_hint` and `content_categories`
- Create enriched subagent tasks
- Filter/route content to appropriate subagents

**Phase 3: SUBAGENT v2.0.0** ⏳ PLANNED
- Receive filtered content from PLANNER
- Focus on single-concern analysis
- Quantify uncertainties

**Phase 4: RISK_ASSESSOR v2.0.0** ⏳ PLANNED
- Rename to "Cross-Functional Synthesizer"
- Remove "VETO POWER" language
- Consolidate findings from all subagents

**Phase 5: WRITER v1.1.0** ⏳ PLANNED
- Add conflict resolution protocol
- Prioritize RISK_ASSESSOR synthesis

### 1.4 Expected Benefits

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Data Loss | ~40% | 0% | **+100%** |
| EXTRACTOR Tokens | 6,500 | 4,000 | -38% |
| Total Pipeline Tokens | ~25,000 | ~22,000 | -12% |
| Schema Flexibility | Low | High | +∞ |
| Agent Independence | Low | High | +∞ |
| Content Visibility | Poor | Excellent | ✅ |

---

## Section 2: EXTRACTOR Agent Refactoring

### 2.1 EXTRACTOR v3.0.0 Architecture

**Goal:** Preserve 100% of document content with zero interpretation

**Design Decisions:**

#### 2.1.1 Content-First Schema

```json
{
  "document_metadata": {...},
  "pages": [
    {
      "page_number": 1,
      "headers": ["All h1/h2/h3 headers"],
      "body_text": "Full page text",
      "tables": [
        {
          "title": "Table caption",
          "interpretation_hint": "voc_measurements | composition_data | ...",
          "headers": ["Col1", "Col2"],
          "rows": [["cell1", "cell2"], ...]
        }
      ],
      "key_value_pairs": [{"key": "...", "value": "..."}],
      "lists": [{"type": "bulleted", "items": [...]}],
      "diagrams_and_images": [...],
      "signatures_and_stamps": [...],
      "content_categories": ["composition", "safety", ...]
    }
  ],
  "quick_facts": {...},
  "extraction_notes": [...]
}
```

**Why `pages[]`?**
- Preserves document structure (page boundaries matter for context)
- No data loss (all content included)
- Easy to navigate (page numbers, headers, sections)
- Supports all document types (SDS, reports, inquiries, permits)

#### 2.1.2 Interpretation Hints (Light Categorization)

**Purpose:** Help PLANNER quickly identify table types without deep analysis

**Categories:**
- `composition_data`: Ingredient lists, CAS + percentages
- `voc_measurements`: Emission data, concentrations
- `toxicity_data`: LD50, LC50, exposure limits
- `process_parameters`: Flow rates, temperatures, pressures
- `regulatory_info`: H-codes, GHS, UN numbers
- `properties`: Physical/chemical properties
- `other`: Unclear or mixed content

**Rule:** When in doubt, use `"other"` rather than wrong category

#### 2.1.3 Quick Facts (Fast Access Layer)

**Purpose:** Allow PLANNER to check for entities without parsing all pages

**Entities Tracked:**
```json
{
  "products_mentioned": ["Product A", "Product B"],
  "cas_numbers_found": ["100-42-5", "13475-82-6"],
  "measurement_units_detected": ["m3/h", "mg/Nm3", "%"],
  "voc_svoc_detected": true,
  "languages_detected": ["de"],
  "companies_mentioned": ["Company X"],
  "locations_mentioned": ["Wuppertal", "Deutschland"]
}
```

**Usage Pattern:**
```python
# Quick check (no page parsing)
if extracted_facts["quick_facts"]["voc_svoc_detected"]:
    # Deep search in pages[]
    voc_tables = find_tables_by_hint(extracted_facts, "voc_measurements")
```

#### 2.1.4 Extraction Notes (Technical Flags)

**Purpose:** Flag ambiguities for PLANNER to resolve

**Status Types:**
- `extraction_uncertain`: Not confident in interpretation
- `missing_in_source`: Data mentioned but incomplete
- `unclear_format`: Ambiguous formatting
- `table_empty`: Structure exists but no data
- `not_provided_in_documents`: Field mentioned but no value

**Format Change (v2.0.0 → v3.0.0):**
```json
// v2.0.0 (OLD)
{
  "field": "pollutant_characterization.voc_list",
  "status": "missing_in_source",
  "note": "VOC mentioned but no values provided"
}

// v3.0.0 (NEW)
{
  "field": "pages[5].tables[2].rows[3]",  // JSON path notation
  "status": "missing_in_source",
  "note": "VOC mentioned but no values provided"
}
```

**Critical:** EXTRACTOR only FLAGS issues, does not:
- Add severity ratings (CRITICAL/HIGH/MEDIUM/LOW) → RISK_ASSESSOR's job
- Assess impact on feasibility → PLANNER's job
- Propose solutions → SUBAGENT's job

### 2.2 Unit Normalization Rules

**Critical for LLM consumption:** Normalize Unicode to ASCII

| Input | Output | Reason |
|-------|--------|--------|
| `m³/h` | `m3/h` | Superscript → ASCII |
| `°C` | `degC` | Unicode symbol → ASCII |
| `Â°C` | `degC` | Encoding issue → ASCII |
| `Nm³/h` | `Nm3/h` | Preserve case, normalize superscript |

**Why ASCII?**
- LLMs handle ASCII more reliably than Unicode
- Prevents encoding issues in downstream processing
- Standardizes units for calculations

### 2.3 Testing EXTRACTOR v3.0.0

**Test Script:** `backend/tests/evaluation/extractor/test_v3_pdf.py`

**Usage:**
```bash
cd backend
source .venv/bin/activate
python3 tests/evaluation/extractor/test_v3_pdf.py Datenblatt_test.pdf
```

**Validation Criteria:**
1. ✅ `pages[]` structure present
2. ✅ All page content preserved (headers, body_text, tables, key_value_pairs)
3. ✅ `interpretation_hint` assigned to tables
4. ✅ `quick_facts` populated
5. ✅ No v2.0.0 schema fields present
6. ✅ JSON parsing succeeds

**Validated Test Case:**
- File: `Datenblatt_test.pdf` (8 pages, mixed SDS + measurement report)
- Output: `test_output_v3_0_0_Datenblatt_test.json` (35.9 KB)
- Result: ✅ ALL CRITERIA PASSED (2025-10-24)

### 2.4 EXTRACTOR Prompt Engineering Best Practices

**Learned from v1.0.0 → v2.0.0 → v3.0.0:**

1. **Be Explicit About JSON Requirements**
   - ❌ "Return valid JSON"
   - ✅ "Output MUST start with { and end with } - no markdown blocks, no explanatory text"

2. **Provide Concrete Examples**
   - ❌ "Extract tables from the document"
   - ✅ Show 2-3 complete example tables with all fields

3. **Use Quality Checklists**
   - End prompt with "Before returning output, verify:"
   - Checklist format forces self-review

4. **Separate Technical Rules from Business Logic**
   - Technical: Unit normalization, encoding cleanup
   - Business: Carcinogen detection, risk assessment (remove from EXTRACTOR)

5. **Use Field Path Notation for Debugging**
   - `pages[5].tables[2].rows[3]` is more useful than `"voc_list"`

### 2.5 Migration Impact

**Breaking Changes:** YES - Complete output format change

**Downstream Dependencies:**
- **PLANNER v2.1.0** (REQUIRED): Must consume `pages[]` format
- **SUBAGENT v2.0.0** (OPTIONAL): Can benefit from filtered content
- **RISK_ASSESSOR v2.0.0** (OPTIONAL): No direct dependency
- **WRITER v1.1.0** (OPTIONAL): No direct dependency

**Rollback Plan:**
```bash
# In .env file
EXTRACTOR_PROMPT_VERSION=v2.0.0  # Roll back to v2.0.0
```

**Testing Before Production:**
1. Unit test: EXTRACTOR v3.0.0 with 10+ historical documents
2. Integration test: EXTRACTOR v3.0.0 → PLANNER v2.1.0 pipeline
3. E2E test: Full pipeline with diverse document types
4. A/B test: Compare v2.0.0 vs v3.0.0 outputs for data loss

### 2.6 Lessons Learned

**What Worked:**
- ✅ Content-first philosophy eliminated data loss
- ✅ `interpretation_hint` helps PLANNER without forcing categorization
- ✅ `quick_facts` enables fast entity access without page parsing
- ✅ JSON path notation in `extraction_notes` improves debugging

**What Didn't Work (v2.0.0):**
- ❌ Schema-first forcing caused 40% data loss
- ❌ Predefined fields couldn't handle all document types
- ❌ Mixed concerns (extraction + business logic) bloated prompts

**Key Insight:**
> "The EXTRACTOR's job is to be a faithful recorder, not an interpreter. Interpretation is the PLANNER's domain."

---

## Section 3: PLANNER Agent Refactoring

### 3.1 PLANNER v2.1.0 Requirements

**Status:** 🔧 IN PROGRESS

**Goal:** Consume EXTRACTOR v3.0.0 `pages[]` format and create enriched subagent tasks

**Key Changes:**

1. **Input Format Change**
   - OLD: Read structured fields (`pollutant_characterization`, `process_parameters`)
   - NEW: Parse `pages[]` using `interpretation_hint` and `content_categories`

2. **Content Interpretation**
   - Use `quick_facts` for fast entity checks
   - Filter tables by `interpretation_hint`
   - Filter pages by `content_categories`
   - Extract relevant content for each subagent

3. **Subagent Task Enrichment**
   - Provide filtered content to subagents (not all pages)
   - Include relevant page numbers and table references
   - Add context from `quick_facts`

**Design Pattern:**
```python
# PLANNER v2.1.0 pseudo-code

def create_voc_analysis_subagent(extracted_facts):
    """Example: Create VOC analysis subagent with filtered content"""

    # Quick check
    if not extracted_facts["quick_facts"]["voc_svoc_detected"]:
        return None  # Skip this subagent

    # Find relevant tables
    voc_tables = [
        {
            "page": page["page_number"],
            "table": table
        }
        for page in extracted_facts["pages"]
        for table in page.get("tables", [])
        if table.get("interpretation_hint") == "voc_measurements"
    ]

    # Create subagent task
    return {
        "subagent_name": "VOC Composition Analyzer",
        "task_description": "Analyze VOC composition from measurement tables",
        "input_context": {
            "voc_tables": voc_tables,
            "cas_numbers": extracted_facts["quick_facts"]["cas_numbers_found"],
            "products": extracted_facts["quick_facts"]["products_mentioned"]
        },
        "tools_needed": ["product_database", "oxytec_knowledge_search"]
    }
```

### 3.2 PLANNER v2.1.0 Development Plan

**Timeline:** 2-3 days

**Tasks:**
1. Update input parsing logic to read `pages[]`
2. Implement table filtering by `interpretation_hint`
3. Implement page filtering by `content_categories`
4. Add `quick_facts` entity extraction
5. Update subagent task templates to include filtered content
6. Write integration tests (EXTRACTOR v3.0.0 → PLANNER v2.1.0)
7. Update prompt file: `backend/app/agents/prompts/versions/planner_v2_1_0.py`
8. Update config: `planner_prompt_version = "v2.1.0"`

**Acceptance Criteria:**
- [ ] PLANNER successfully consumes v3.0.0 output
- [ ] Subagents receive filtered, relevant content
- [ ] No data loss compared to v1.0.0 → v2.0.0 pipeline
- [ ] Integration tests pass with 5+ document types

---

## Section 4: SUBAGENT Agent Refactoring

**Status:** ⏳ PLANNED

**Goal:** Receive filtered content from PLANNER v2.1.0 and perform focused analysis

**Planned Changes:**
- Input context clarification (receive only relevant pages/tables)
- Uncertainty quantification requirements
- Single-concern focus (one analysis per subagent)

**Timeline:** 1-2 days (after PLANNER v2.1.0)

---

## Section 5: RISK_ASSESSOR Agent Refactoring

**Status:** ⏳ PLANNED

**Goal:** Rename to "Cross-Functional Synthesizer" and consolidate all findings

**Planned Changes:**
- Remove "VETO POWER" language
- Add synthesis logic for conflicting subagent outputs
- Quantify overall project risk (probability × impact)

**Timeline:** 2-3 days (after SUBAGENT v2.0.0)

---

## Section 6: WRITER Agent Refactoring

**Status:** ⏳ PLANNED

**Goal:** Add conflict resolution protocol

**Planned Changes:**
- Prioritize RISK_ASSESSOR synthesis over individual subagent findings
- Handle conflicting recommendations
- Improve German report quality

**Timeline:** 1-2 days (after RISK_ASSESSOR v2.0.0)

---

## Related Documentation

- **Architecture Overview:** `docs/architecture/AGENT_REFACTORING_ARCHITECTURE.md`
- **EXTRACTOR Migration Guide:** `docs/implementation/EXTRACTOR_v3.0.0_MIGRATION_GUIDE.md`
- **Prompt Changelog:** `docs/development/PROMPT_CHANGELOG.md`
- **Versioning Guide:** `backend/app/agents/prompts/versions/README.md`
- **Project Instructions:** `CLAUDE.md`

---

## Contact

**Project Owner:** Andreas
**Status:** Section 1 & 2 Complete (EXTRACTOR v3.0.0 ✅)
**Next:** Section 3 (PLANNER v2.1.0 🔧 IN PROGRESS)

---

**Last Updated:** 2025-10-24
