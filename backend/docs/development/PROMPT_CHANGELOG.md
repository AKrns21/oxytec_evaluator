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

### PLANNER v1.0.0 (2025-10-23)

**Type:** BASELINE
**Status:** 🟢 Active
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

**Next Version:** v2.1.0 (planned) - Will consume EXTRACTOR v3.0.0 `pages[]` format

---

## SUBAGENT Agent

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
