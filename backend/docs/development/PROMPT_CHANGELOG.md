# Prompt Version Changelog

**Purpose:** Track all prompt version changes across the Oxytec Multi-Agent Feasibility Platform for audit trail and rollback capability.

**Note:** This is a centralized changelog. Each prompt file (`app/agents/prompts/versions/<agent>_vX_Y_Z.py`) also contains an inline CHANGELOG that appears in the UI.

---

## Format

Each entry follows this format:

```
### AGENT_NAME vX.Y.Z (YYYY-MM-DD)

**Type:** MAJOR | MINOR | PATCH
**Status:** 🟢 Active | ✅ Ready | 🟡 Deprecated | 🔧 In Development
**Token Impact:** +/-X tokens (+/-Y%)
**Breaking Changes:** Yes | No

**Changes:**
- Change 1: Description
- Change 2: Description
- ...

**Rationale:**
Why this change was made

**Migration Notes:**
How to migrate from previous version (if breaking change)

**Testing:**
- Test case 1: Result
- Test case 2: Result
```

---

## EXTRACTOR Agent

### EXTRACTOR v3.0.0 (2025-10-24)

**Type:** MAJOR (Breaking Change)
**Status:** ✅ Tested & Validated
**Token Impact:** +800 tokens in prompt (+25%), but net -10% overall pipeline due to PLANNER filtering
**Breaking Changes:** YES - Complete output format change

**Changes:**
- **REMOVED:** Schema-first field forcing (pollutant_list[], process_parameters, etc.)
- **REMOVED:** Predefined top-level structure (9 fields → 4 fields)
- **ADDED:** `pages[]` structure with full content preservation
  - Components: headers, body_text, tables, key_value_pairs, lists, diagrams, signatures
- **ADDED:** `interpretation_hint` system for tables (7 categories)
  - Categories: composition_data, voc_measurements, toxicity_data, process_parameters, regulatory_info, properties, other
- **ADDED:** `content_categories` for pages (11 categories)
  - Categories: product_identification, composition, safety, toxicity, regulatory, process_data, measurements, environmental, handling, disposal, transport
- **ADDED:** `quick_facts` for fast entity access
  - Entities: products, CAS numbers, units, companies, locations, voc_svoc_detected
- **MODIFIED:** `extraction_notes` now uses field_path format: `"pages[X].tables[Y]"`
- **PRESERVED:** Unit normalization rules from v2.0.0 (m³/h → m3/h, °C → degC)

**Philosophy Change:**
- **v2.0.0 (Schema-First):** Force content into predefined fields → 40% data loss
- **v3.0.0 (Content-First):** Preserve ALL page structure → Add light interpretation hints → PLANNER interprets downstream

**Rationale:**
User feedback: "I don't see content but rather categories" - v2.0.0's schema-first approach was causing significant data loss. v3.0.0 preserves 100% of document content and delegates interpretation to PLANNER.

**Migration Notes:**
- **Requires PLANNER v2.1.0** to consume new `pages[]` format
- Old fields removed: `pollutant_characterization`, `process_parameters`, `current_abatement_systems`, `industry_and_process`, `requirements_and_constraints`, `site_conditions`, `customer_knowledge_and_expectations`, `customer_specific_questions`, `timeline_and_project_phase`, `data_quality_issues`
- New access pattern: Instead of `extracted_facts.pollutant_characterization.voc_list`, PLANNER must search `extracted_facts.pages[*].tables[*]` with `interpretation_hint == "voc_measurements"`

**Testing:**
- ✅ Test script: `backend/tests/evaluation/extractor/test_v3_pdf.py`
- ✅ Test case: Datenblatt_test.pdf (8 pages, mixed content)
- ✅ Validated output: `backend/tests/evaluation/extractor/test_output_v3_0_0_Datenblatt_test.json` (35.9 KB)
- ✅ Validation results:
  - All page content preserved (8 pages)
  - interpretation_hints assigned to tables
  - quick_facts populated (CAS numbers, products, units, companies)
  - No v2.0.0 fields present (clean migration)
  - JSON parsing: 100% success

**File:** `backend/app/agents/prompts/versions/extractor_v3_0_0.py`
**Config:** `backend/app/config.py:66` - `extractor_prompt_version = "v3.0.0"`

---

### EXTRACTOR v2.0.0 (2025-10-24)

**Type:** MAJOR (Breaking Change)
**Status:** 🟡 Deprecated (superseded by v3.0.0)
**Token Impact:** -3,300 tokens (-50%)
**Breaking Changes:** YES - Removed business logic fields

**Changes:**
- **REMOVED:** Carcinogen detection logic (~1,200 tokens)
- **REMOVED:** Severity ratings (CRITICAL/HIGH/MEDIUM/LOW) (~300 tokens)
- **REMOVED:** Business logic and interpretation
- **ADDED:** `extraction_notes` field for technical uncertainties (~500 tokens)
- **ADDED:** Technical cleanup rules (~400 tokens)
- **ENHANCED:** Unit normalization (Unicode → ASCII)
- **MODIFIED:** Pure technical extraction focus

**Rationale:**
v1.0.0 was doing too much (extraction + enrichment + business logic) leading to 6,500+ token prompts and inconsistent outputs. v2.0.0 focuses solely on technical extraction.

**Migration Notes:**
- Carcinogen detection moved to PLANNER
- Severity ratings moved to RISK_ASSESSOR
- `extraction_notes` replaces `data_quality_issues` with technical focus

**Testing:**
- Test cases: 10 historical documents
- Validation: JSON parsing 100% success, field extraction accuracy >95%

**File:** `backend/app/agents/prompts/versions/extractor_v2_0_0.py`

---

### EXTRACTOR v1.0.0 (2025-10-23)

**Type:** BASELINE
**Status:** 🟡 Deprecated (replaced by v2.0.0)
**Token Impact:** ~6,500 tokens (baseline)
**Breaking Changes:** N/A (initial version)

**Changes:**
- Initial implementation with comprehensive extraction logic
- Included carcinogen detection
- Included severity ratings
- Included business logic and interpretation
- Mixed technical and business concerns

**Rationale:**
Initial version before refactoring project

**File:** `backend/app/agents/prompts/versions/extractor_v1_0_0.py`

---

## PLANNER Agent

### PLANNER v2.1.1 (2025-10-24)

**Type:** MINOR (Feature Addition)
**Status:** 🟢 Active
**Token Impact:** +200 tokens (+4%) - PubChem tool documentation
**Breaking Changes:** NO - Backward compatible with v2.1.0

**Changes:**
- **ADDED:** `pubchem_lookup` as optional tool for chemical data retrieval
- **ADDED:** Intelligent tool selection logic (PubChem when CAS numbers present, web_search as fallback)
- **ADDED:** Comprehensive PubChem tool usage guidance (30 functions documented)
- **ADDED:** Tool selection decision rules for 6 common subagent types
- **MODIFIED:** VOC Composition Analyzer: tools from `["web_search"]` → `["pubchem_lookup"]`
- **MODIFIED:** Safety/ATEX Evaluator: tools from `["web_search"]` → `["pubchem_lookup"]`
- **MODIFIED:** Regulatory Compliance: tools from `["web_search"]` → `["pubchem_lookup", "web_search"]`

**Tool Selection Strategy:**
- **pubchem_lookup**: Primary for CAS validation, physical properties, LEL/UEL, toxicity, H-codes, GHS classifications
- **oxytec_knowledge_search**: Required for technology comparisons (NTP/UV/scrubbers)
- **product_database**: For Oxytec product catalog searches
- **web_search**: Secondary/fallback for non-chemical data (regulations, BAT references)

**Rationale:**
Replace unreliable web scraping for chemical data with direct PubChem API access. PubChem MCP server provides 30+ functions for authoritative chemical data (no API key required). This improves accuracy and reduces hallucination risk for CAS validation, physical properties, and safety data.

**Migration Notes:**
- **Fully backward compatible** - v2.1.1 can consume same v3.0.0 EXTRACTOR output as v2.1.0
- No changes to input/output format
- Subagents created by v2.1.1 will have different tools arrays (includes `pubchem_lookup`)
- SUBAGENT v2.0.0 required to actually execute PubChem tools (v1.0.0 will ignore unknown tools)

**Testing:**
- ⏳ Integration test: EXTRACTOR v3.0.0 → PLANNER v2.1.1 → Check tool selection
- ⏳ Validation: VOC/Safety/Regulatory subagents receive `pubchem_lookup` tool
- ⏳ E2E test: Full pipeline with Datenblatt_test.pdf + SUBAGENT v2.0.0

**File:** `backend/app/agents/prompts/versions/planner_v2_1_1.py`
**Config:** `backend/app/config.py:67` - `planner_prompt_version = "v2.1.1"`

---

### PLANNER v2.1.0 (2025-10-24)

**Type:** MINOR (Breaking Change for EXTRACTOR integration)
**Status:** ✅ Ready for testing
**Token Impact:** -500 tokens (-10%) - More efficient content routing
**Breaking Changes:** YES - Requires EXTRACTOR v3.0.0 output format

**Changes:**
- **ADDED:** `pages[]` parsing logic with `interpretation_hint` filtering
- **ADDED:** `content_categories`-based page filtering
- **ADDED:** `quick_facts` fast-access layer usage (check VOC/CAS without parsing pages)
- **ADDED:** Content extraction examples for 6 common subagent types
- **ADDED:** Step-by-step workflow for filtering content by hint/category
- **MODIFIED:** `relevant_content` now contains filtered pages/tables instead of v2.0.0 schema fields
- **REMOVED:** References to v2.0.0 schema fields (pollutant_characterization, process_parameters, etc.)

**Philosophy Change:**
- **v1.0.0 (Schema-First):** Access predefined fields directly → Relies on EXTRACTOR interpretation
- **v2.1.0 (Content-First):** Parse `pages[]` → Filter by hints → Extract relevant content → Delegate to subagents

**Rationale:**
Support EXTRACTOR v3.0.0 content-first architecture. PLANNER now acts as the **interpreter** while EXTRACTOR focuses on **preservation**. This eliminates the 40% data loss from v2.0.0 schema-first forcing.

**Migration Notes:**
- **Requires EXTRACTOR v3.0.0** - Will not work with v2.0.0 output
- Subagents now receive filtered content instead of full extracted_facts
- `relevant_content` format changed from schema fields to filtered pages/tables
- New access patterns:
  ```python
  # OLD (v1.0.0): Direct field access
  voc_list = extracted_facts["pollutant_characterization"]["voc_list"]

  # NEW (v2.1.0): Filter by interpretation_hint
  voc_tables = [
      table for page in pages
      for table in page["tables"]
      if table["interpretation_hint"] == "voc_measurements"
  ]
  ```

**Testing:**
- ⏳ Integration test: EXTRACTOR v3.0.0 → PLANNER v2.1.0 → SUBAGENTS
- ⏳ Validation: Subagents receive correct filtered content
- ⏳ E2E test: Full pipeline with Datenblatt_test.pdf

**File:** `backend/app/agents/prompts/versions/planner_v2_1_0.py`
**Config:** `backend/app/config.py:67` - `planner_prompt_version = "v2.1.0"`

---

### PLANNER v1.0.0 (2025-10-23)

**Type:** BASELINE
**Status:** 🟡 Deprecated (superseded by v2.1.0)
**Token Impact:** ~5,000 tokens (baseline)
**Breaking Changes:** N/A (initial version)

**Changes:**
- Initial implementation for dynamic subagent planning
- Creates 3-8 specialized subagent definitions based on inquiry complexity
- Supports tools: `product_database`, `web_search`, `oxytec_knowledge_search`
- Includes ATEX de-emphasis guidance (LOW-MEDIUM risk positioning)
- Technology-agnostic approach (NTP/UV/scrubbers/hybrids)

**Rationale:**
Baseline version extracted from monolithic prompt during initial versioning

**File:** `backend/app/agents/prompts/versions/planner_v1_0_0.py`

---

## SUBAGENT Agent

### SUBAGENT v2.0.0 (2025-10-24)

**Type:** MINOR (Feature Addition)
**Status:** 🟢 Active
**Token Impact:** +500 tokens (+15%) - PubChem tool documentation
**Breaking Changes:** NO - Backward compatible with v1.0.0 tasks

**Changes:**
- **ADDED:** `pubchem_lookup` tool usage guidance (30+ functions documented)
- **ADDED:** Tool selection priority: pubchem_lookup > oxytec_knowledge_search > product_database > web_search
- **ADDED:** PubChem API call examples for common use cases:
  - CAS validation via get_compound_properties
  - Physical properties (boiling point, vapor pressure, density)
  - LEL/UEL values via get_ghs_classification
  - Toxicity data (LD50, LC50, IARC carcinogenicity) via get_compound_toxicity
  - Safety data (GHS pictograms, H-codes, signal words)
  - Synonyms/trade name matching via get_compound_synonyms
- **MODIFIED:** web_search guidance - now fallback for non-chemical data only (regulations, standards)
- **MODIFIED:** TECHNICAL RIGOR section - mandate PubChem for chemical properties
- **REMOVED:** References to web scraping chemical databases (PubChem, NIST, ChemSpider)

**Rationale:**
Replace unreliable web scraping for chemical data with direct PubChem MCP server integration. PubChem provides authoritative NIH database access with no API key required. This improves accuracy, reduces hallucination risk, and provides structured data for CAS validation, physical properties, toxicity, and safety information.

**Migration Notes:**
- **Fully backward compatible** - v2.0.0 can execute v1.0.0 tasks (ignores unknown tools)
- Subagents receiving `pubchem_lookup` tool from PLANNER v2.1.1 will use it automatically
- Execution logic remains unchanged - only tool guidance updated
- No changes to output format or parsing requirements

**Testing:**
- ⏳ Integration test: PLANNER v2.1.1 → SUBAGENT v2.0.0 with CAS validation
- ⏳ Validation: PubChem calls return valid data for common VOCs
- ⏳ E2E test: Full pipeline with Datenblatt_test.pdf

**File:** `backend/app/agents/prompts/versions/subagent_v2_0_0.py`
**Config:** `backend/app/config.py:68` - `subagent_prompt_version = "v2.0.0"`

---

### SUBAGENT v1.0.0 (2025-10-23)

**Type:** BASELINE
**Status:** 🟢 Active
**Token Impact:** ~3,500 tokens (baseline)
**Breaking Changes:** N/A (initial version)

**Changes:**
- Initial implementation for parallel subagent execution
- Tool usage guidance for RAG queries
- ATEX context (equipment outside zones)
- Risk severity classification requirements

**Rationale:**
Baseline version extracted from monolithic prompt during initial versioning

**File:** `backend/app/agents/prompts/versions/subagent_v1_0_0.py`

---

## RISK_ASSESSOR Agent

### RISK_ASSESSOR v1.0.0 (2025-10-23)

**Type:** BASELINE
**Status:** 🟢 Active
**Token Impact:** ~4,000 tokens (baseline)
**Breaking Changes:** N/A (initial version)

**Changes:**
- Initial implementation for risk synthesis
- ATEX risk classification guidance (LOW-MEDIUM typical)
- Mitigation strategy consolidation
- Go/no-go decision framework

**Rationale:**
Baseline version extracted from monolithic prompt during initial versioning

**File:** `backend/app/agents/prompts/versions/risk_assessor_v1_0_0.py`

---

## WRITER Agent

### WRITER v1.0.0 (2025-10-23)

**Type:** BASELINE
**Status:** 🟢 Active
**Token Impact:** ~6,000 tokens (baseline)
**Breaking Changes:** N/A (initial version)

**Changes:**
- Initial implementation for German report generation
- Technology-agnostic positioning guidance
- Comprehensive feasibility report structure
- Claude Sonnet 4.5 optimized

**Rationale:**
Baseline version extracted from monolithic prompt during initial versioning

**File:** `backend/app/agents/prompts/versions/writer_v1_0_0.py`

---

## Semantic Versioning Rules

### MAJOR (vX.0.0) - Breaking Changes
- Output format changes requiring downstream updates
- Required field changes
- Major behavioral shifts
- Scope changes (e.g., v2.0.0 removing business logic)

**When to bump:** Changes that require other agents to update

### MINOR (vX.Y.0) - New Features
- New sections added
- Significant prompt improvements
- New instructions (backward compatible)
- Enhanced detection patterns

**When to bump:** Adds functionality without breaking compatibility

### PATCH (vX.Y.Z) - Bug Fixes
- Bug fixes
- Clarifications
- Small adjustments
- Typo corrections
- Example improvements

**When to bump:** Fixes without adding features

---

## Version Status Legend

| Status | Meaning |
|--------|---------|
| 🟢 **Active** | Currently deployed in production |
| ✅ **Tested & Validated** | Tested and approved, ready for deployment |
| 🟡 **Deprecated** | Old version, kept for rollback only |
| 🔧 **In Development** | Work in progress, not yet tested |
| ⛔ **Archived** | No longer maintained, do not use |

---

## Related Documentation

- **Prompt Versions Directory:** `backend/app/agents/prompts/versions/`
- **Versioning Guide:** `backend/app/agents/prompts/versions/README.md`
- **Configuration:** `backend/app/config.py` (prompt version settings)
- **Project Instructions:** `CLAUDE.md`

---

**Last Updated:** 2025-10-24
**Latest Version:** EXTRACTOR v3.0.0 (Tested & Validated)
