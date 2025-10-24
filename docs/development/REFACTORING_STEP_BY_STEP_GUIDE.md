# Agent Refactoring: Step-by-Step Implementation Guide

**Date:** 2025-10-23
**For:** Development Team
**Prerequisites:** Phase 1 (Prompt Versioning Infrastructure) ✅ Complete

---

## Quick Start

```bash
# Clone and setup
cd backend
source .venv/bin/activate

# Verify infrastructure is ready
python3 -c "from app.agents.prompts.versions import get_prompt_version; print(get_prompt_version('extractor', 'v1.0.0')['VERSION'])"
# Should output: v1.0.0

# Start with EXTRACTOR refactoring
cd app/agents/prompts/versions
cp extractor_v1_0_0.py extractor_v2_0_0.py
```

---

## Phase 2: EXTRACTOR Refactoring (Week 1)

### Step 1: Create EXTRACTOR v2.0.0

**File:** `backend/app/agents/prompts/versions/extractor_v2_0_0.py`

**Copy and edit:**
```bash
cd backend/app/agents/prompts/versions
cp extractor_v1_0_0.py extractor_v2_0_0.py
```

**Changes to make in `extractor_v2_0_0.py`:**

#### 1.1 Update Version Metadata

```python
VERSION = "v2.0.0"

CHANGELOG = """
v2.0.0 (2025-10-23) - BREAKING: Remove business logic, add extraction_notes
- REMOVED: Carcinogen detection and flagging (lines 47-94 from v1.0.0)
- REMOVED: Severity rating from data_quality_issues (lines 394-407)
- REMOVED: Carcinogen flagging examples (lines 491-531)
- REMOVED: Hardcoded example document "Mathis_input.txt" (lines 96-109)
- ADDED: extraction_notes system for flagging data issues without severity assessment
- ADDED: Technical cleanup rules (unit normalization, number formatting, CAS extraction)
- CHANGED: data_quality_issues → empty array (deprecated, use extraction_notes instead)

Reference: docs/architecture/agent_refactoring_instructions.md lines 24-184
"""
```

#### 1.2 Remove Carcinogen Detection Section

**Find and DELETE these lines (~lines 47-120 in v1.0.0):**
```python
# DELETE THIS ENTIRE SECTION:
from app.agents.prompts import CARCINOGEN_DATABASE

PROMPT_TEMPLATE = f"""
...
{CARCINOGEN_DATABASE}  # ❌ REMOVE THIS
...
**CARCINOGENIC & HIGHLY TOXIC SUBSTANCES:**  # ❌ REMOVE THIS ENTIRE SECTION
...
**AUTOMATIC ESCALATION RULES:**  # ❌ REMOVE THIS
...
"""
```

**Rationale:** Carcinogen risk assessment is PLANNER's job (creates Carcinogen Risk Subagent if needed).

#### 1.3 Add EXTRACTION_NOTES Section

**Add AFTER the initial task description (~line 20):**

```python
PROMPT_TEMPLATE = """
# Your Task
You are a technical data extraction specialist. Extract structured facts from industrial inquiry documents.

**EXTRACTION NOTES:**

When you encounter missing, unclear, or ambiguous data during extraction, add a note to the "extraction_notes" array:

{
  "extraction_notes": [
    {
      "field": "path.to.field (e.g., pollutant_list[0].cas_number)",
      "status": "not_provided_in_documents | missing_in_source | unclear_format | table_empty | extraction_uncertain",
      "note": "Brief description of what is missing/unclear"
    }
  ]
}

**Status Types:**
- `not_provided_in_documents`: Field exists in schema but is not mentioned anywhere in documents
- `missing_in_source`: Mentioned but incomplete (e.g., substance name without CAS number)
- `unclear_format`: Present but ambiguous (e.g., "m3/h" vs "Nm3/h" unclear, or "150" without unit)
- `table_empty`: Table structure exists but cells are empty
- `extraction_uncertain`: You are unsure if you interpreted the data correctly

**Examples:**

Document says: "Ethylacetat"
→ extraction_notes: {{"field": "pollutant_list[0].cas_number", "status": "missing_in_source", "note": "Ethylacetat mentioned without CAS number"}}

Document says: "156 kg/Tag Ethylacetat"
→ extraction_notes: {{"field": "pollutant_list[0].concentration", "status": "unclear_format", "note": "Document states '156 kg/Tag' but unclear if this is concentration (mg/Nm3) or daily load (kg/day)"}}

Document mentions "Ablufttemperatur" but no value given
→ extraction_notes: {{"field": "process_parameters.temperature.value", "status": "not_provided_in_documents", "note": "Temperature mentioned but no value provided"}}

**DO NOT:**
- Add severity ratings (CRITICAL/HIGH/MEDIUM/LOW)
- Add impact descriptions ("Affects LEL calculations...")
- Make business judgments about what is important
- Propose solutions or workarounds

Your job is to FLAG what's missing, not to ASSESS its impact.

---

**TECHNICAL CLEANUP RULES:**

You MUST perform these automatic technical normalizations:

1. **Unit Normalization:**
   - Unicode → ASCII: "m³/h" → "m3/h", "°C" → "degC", "Â°C" → "degC"
   - Preserve original case: "Nm3/h" stays "Nm3/h" (do NOT lowercase)
   - Preserve ambiguity: If document doesn't specify "m3/h" vs "Nm3/h", extract as written and add extraction_note

2. **Number Formatting:**
   - Thousand separators: "1.200" (German) → 1200, "1,200" (English) → 1200
   - Decimal separators: Preserve "1.5" as 1.5, "1,5" as 1.5
   - Ranges: "10-20%" → extract as string "10-20%" in formulation_percentage field

3. **Text Preservation:**
   - Preserve original substance names exactly: "Ethylacetat" stays "Ethylacetat" (do NOT translate to "Ethyl acetate")
   - Preserve original wording in free-text fields
   - Do NOT correct spelling errors (that's not your job)

4. **Table Extraction:**
   - Extract ALL rows and columns, including empty cells (use null for empty)
   - Preserve header text exactly as written
   - Preserve row order

5. **CAS Number Extraction:**
   - Extract if present in document: "CAS: 141-78-6" → "141-78-6"
   - If missing: cas_number: null (do NOT look up!)
   - If ambiguous: Add extraction_note

**DO NOT:**
- Look up missing CAS numbers (planner's job)
- Translate substance names (planner's job)
- Validate if numbers are physically plausible (planner's job)
- Normalize "m3/h" vs "Nm3/h" unless document is explicit (flag ambiguity instead)

---

... [rest of prompt] ...
"""
```

#### 1.4 Update JSON Schema

**Find the OUTPUT SCHEMA section and UPDATE:**

```python
PROMPT_TEMPLATE = """
...

## Output Schema

Return a JSON object with this structure:

{
  "extraction_notes": [
    {
      "field": "string (JSON path to field, e.g., pollutant_list[0].cas_number)",
      "status": "string (not_provided_in_documents | missing_in_source | unclear_format | table_empty | extraction_uncertain)",
      "note": "string (brief description)"
    }
  ],
  "data_quality_issues": [],  // DEPRECATED - Leave as empty array for backward compatibility
  "pollutant_list": [ ... ],
  "process_parameters": { ... },
  ... [rest of schema unchanged] ...
}

**IMPORTANT:**
- The "data_quality_issues" field remains in schema (empty array) for backward compatibility
- Use "extraction_notes" for all new data quality flagging
- Do NOT populate data_quality_issues with severity ratings
"""
```

#### 1.5 Remove Example Document

**DELETE hardcoded example document (if present):**

```python
# ❌ DELETE THIS:
**Example Document:**
```
Anfrage: Mathis GmbH
Prozess: Druckguss
...
```
```

**Rationale:** Examples bloat the prompt and aren't representative of all cases.

### Step 2: Test EXTRACTOR v2.0.0

```bash
# Run unit tests
pytest tests/unit/test_extractor_schema.py -v

# Expected: Tests pass with new schema (extraction_notes present, data_quality_issues empty)
```

**Create test case for extraction_notes:**

```python
# tests/unit/test_extractor_schema.py

def test_extraction_notes_schema():
    """Test that extraction_notes are correctly structured."""
    result = {
        "extraction_notes": [
            {
                "field": "pollutant_list[0].cas_number",
                "status": "missing_in_source",
                "note": "Ethylacetat mentioned without CAS"
            }
        ],
        "data_quality_issues": [],
        "pollutant_list": [{"name": "Ethylacetat", "cas_number": None}]
    }

    # Validate schema
    assert "extraction_notes" in result
    assert len(result["extraction_notes"]) > 0
    assert result["extraction_notes"][0]["field"] == "pollutant_list[0].cas_number"
    assert result["extraction_notes"][0]["status"] == "missing_in_source"
    assert result["data_quality_issues"] == []  # Should be empty
```

### Step 3: A/B Compare v1.0.0 vs v2.0.0

```bash
# Test with v1.0.0 (baseline)
EXTRACTOR_PROMPT_VERSION=v1.0.0 python3 scripts/run_inquiry.py tests/data/inquiry_001.pdf > results_v1_0_0.json

# Test with v2.0.0 (new version)
EXTRACTOR_PROMPT_VERSION=v2.0.0 python3 scripts/run_inquiry.py tests/data/inquiry_001.pdf > results_v2_0_0.json

# Compare
python3 scripts/compare_extractions.py results_v1_0_0.json results_v2_0_0.json
```

**Expected differences:**
- v2.0.0: No carcinogen flags in data_quality_issues
- v2.0.0: extraction_notes populated (v1.0.0 has empty array or doesn't exist)
- v2.0.0: data_quality_issues is empty array
- v2.0.0: Prompt ~50% shorter (carcinogen detection removed)

### Step 4: Update Config and Deploy

```bash
# Update config
# Edit backend/app/config.py
```

```python
# backend/app/config.py

class Settings(BaseSettings):
    ...
    extractor_prompt_version: str = Field(default="v2.0.0")  # Changed from v1.0.0
    ...
```

```bash
# Update CHANGELOG
cat >> docs/development/PROMPT_CHANGELOG.md << 'EOF'

## EXTRACTOR

### v2.0.0 (2025-10-23) - BREAKING CHANGE

**Changes:**
- REMOVED: Carcinogen detection and severity assessment (delegated to PLANNER → Carcinogen Risk Subagent)
- REMOVED: Hardcoded example documents
- ADDED: extraction_notes system for flagging data issues without severity
- ADDED: Technical cleanup rules (unit normalization, CAS extraction rules)
- DEPRECATED: data_quality_issues (empty array for backward compatibility)

**Impact:**
- Prompt size reduced from 12,000 to 6,000 characters (-50%)
- Clearer role: Pure technical extraction, no business logic
- Better data quality flagging with extraction_notes

**Reference:** docs/architecture/agent_refactoring_instructions.md lines 24-184

**Testing:** 10 historical inquiries tested - all pass schema validation
EOF

# Commit
git add app/agents/prompts/versions/extractor_v2_0_0.py
git add app/config.py
git add docs/development/PROMPT_CHANGELOG.md
git commit -m "[PROMPT][EXTRACTOR] v2.0.0: BREAKING - Remove business logic, add extraction_notes"
git tag prompt-extractor-v2.0.0
git push origin main --tags

# Restart server
uvicorn app.main:app --reload
```

### Step 5: Validation Checklist

- [ ] No business logic remains (no severity ratings, no impact assessments)
- [ ] extraction_notes section is clear and has examples
- [ ] Technical cleanup rules are explicit
- [ ] CAS lookup is explicitly forbidden
- [ ] Carcinogen detection is completely removed
- [ ] Example document removed
- [ ] JSON schema includes extraction_notes field
- [ ] data_quality_issues remains as empty array (backward compatibility)
- [ ] Tests pass
- [ ] A/B comparison shows expected differences
- [ ] CHANGELOG updated
- [ ] Git tagged

---

## Phase 3: PLANNER Refactoring (Week 2)

### Step 1: Create PLANNER v2.0.0

```bash
cd backend/app/agents/prompts/versions
cp planner_v1_0_0.py planner_v2_0_0.py
```

**Edit `planner_v2_0_0.py`:**

#### 1.1 Update Version Metadata

```python
VERSION = "v2.0.0"

CHANGELOG = """
v2.0.0 (2025-10-23) - BREAKING: Add Phase 1 enrichment, refine orchestration
- ADDED: Phase 1 - Data Enrichment (CAS lookup, standard assumptions, unit disambiguation)
- ADDED: Phase 2 - Subagent Task Creation with conditional logic
- ADDED: Decision tree for which subagents to create (8 specialist types)
- ADDED: enrichment_summary and enrichment_notes in output
- CHANGED: Output structure now includes enriched_facts and data_uncertainties
- REFINED: Planner role - pure orchestrator, NO technology recommendations or risk assessments

Reference: docs/architecture/agent_refactoring_instructions.md lines 188-420
"""
```

#### 1.2 Add PHASE 1: DATA ENRICHMENT Section

```python
PROMPT_TEMPLATE = """
# Your Role
You are the Planner agent in a multi-agent feasibility analysis system.

**PHASE 1: DATA ENRICHMENT (You perform this yourself)**

Before creating subagent tasks, you must clean and enrich the extracted data:

**1. CAS Number Lookup:**
- For any pollutant without cas_number: Use web_search to find it
- Query pattern: "[substance name] CAS number"
- Validate: CAS format is XXX-XX-X or XXXX-XX-X or XXXXX-XX-X
- Add to enriched_facts.json

**2. Standard Value Assumptions:**
- If oxygen_content_percent is null AND no process context suggests otherwise:
  - Assume 21% (atmospheric air)
  - Add note: "Assumed 21% O₂ (atmospheric air) - not measured"
- If pressure.type is null: Assume "atmospheric"
- If humidity is null: Flag as "unknown - affects adsorption/oxidation performance"

**3. Unit Disambiguation:**
- If flow_rate has unit "m3/h" but temperature is known:
  - Calculate Nm3/h equivalent: Nm3/h = m3/h × (273.15 / (273.15 + T_celsius))
  - Add both values to enriched_facts
  - Note: "Calculated from actual m3/h using T=[X]°C"
- If unit is ambiguous (unclear from document): Keep as-is and add uncertainty note

**4. Inconsistency Resolution:**
- If multiple documents give different values for same parameter:
  - Priority: Most recent document > Measurement report > Questionnaire
  - Document which source was used
  - Flag other values as "conflicting data from [source]"

**5. Name Normalization:**
- Look up IUPAC names for substances if helpful (but preserve original name)
- Example: "Ethylacetat" → Add iupac_name: "Ethyl acetate", keep name: "Ethylacetat"

**OUTPUT: enriched_facts.json**
- Same structure as extracted_facts.json but with filled gaps
- Add field "enrichment_notes" documenting what you added/assumed
- Add field "data_uncertainties" for things you couldn't resolve

**TOOLS TO USE:**
- web_search for CAS lookups, substance properties
- Basic calculations for unit conversions (you can do this without tools)

**IMPORTANT:**
- Document every assumption you make
- Be conservative: Only add standard values where clearly applicable
- If uncertain, leave as null and flag for subagent investigation

---

**PHASE 2: SUBAGENT TASK CREATION**

Now that you have clean, enriched data, decompose the analysis into specialized subagent tasks.

**YOUR ROLE: Pure Orchestrator**
- You delegate analysis, you do NOT perform it yourself
- You do NOT make technology recommendations
- You do NOT assess risks or classify severity
- You do NOT make business judgments

**DECISION LOGIC: Which Subagents to Create**

Analyze enriched_facts and data_uncertainties to decide which subagents are needed:

1. **VOC Chemistry Specialist** (ALWAYS create)
   - Trigger: Any VOCs in pollutant_list
   - Task: Analyze reactivity, oxidation pathways, by-products
   - Pass: pollutant_list, process_parameters

2. **Technology Screening Specialist** (ALWAYS create)
   - Trigger: Always needed
   - Task: Compare NTP, UV/ozone, scrubbers quantitatively
   - Pass: pollutant_list, process_parameters, requirements_and_constraints
   - Tools: ["oxytec_knowledge_search", "web_search"]

3. **Safety/ATEX Specialist** (CONDITIONAL)
   - Trigger: IF atex_classification is null OR oxygen_content unknown OR VOC concentration >10% LEL
   - Task: Calculate LEL, assess ATEX zone classification
   - Pass: pollutant_list, process_parameters, site_conditions
   - Note in task: "O₂ assumed 21% - quantify uncertainty in LEL calculation"

4. **Carcinogen Risk Specialist** (CONDITIONAL)
   - Trigger: IF any substance name contains: formaldehyde, ethylene oxide, propylene oxide, benzene, acetaldehyde, H2S
            OR industry_sector contains: surfactant, ethoxylation, petroleum, waste oil, bilge
            OR any alcohol in VOC list (formaldehyde formation risk)
   - Task: Identify Group 1/2A carcinogens, assess formation risks, regulatory implications
   - Pass: pollutant_list, industry_and_process
   - Tools: ["web_search"]

5. **Flow/Mass Balance Specialist** (CONDITIONAL)
   - Trigger: IF flow_rate unit ambiguity OR need reactor sizing OR GHSV calculations
   - Task: Convert units, calculate mass loads, estimate residence times
   - Pass: pollutant_list, process_parameters

6. **Economic Analysis Specialist** (CONDITIONAL)
   - Trigger: IF budget_constraints mentioned OR customer asks for cost comparison
   - Task: Estimate CAPEX/OPEX ranges using product database
   - Pass: technology recommendations (depends on Technology Screening), process_parameters
   - Tools: ["product_database"]
   - **CRITICAL INSTRUCTION:** "Use ONLY product_database for cost data. If no pricing available, state 'Cost TBD - requires quotation'"

7. **Regulatory Compliance Specialist** (CONDITIONAL)
   - Trigger: IF regulatory_requirements mentions TA Luft, IED BAT, EPA, or IF carcinogens present
   - Task: Assess compliance requirements, emission limits, monitoring obligations
   - Pass: pollutant_list, requirements_and_constraints, carcinogen findings
   - Tools: ["web_search"]

8. **Customer Question Response Specialist** (HIGH PRIORITY - CONDITIONAL)
   - Trigger: IF customer_specific_questions array has ≥1 entry
   - Task: Provide direct, numbered answers to customer questions
   - Pass: customer_specific_questions, enriched_facts (relevant sections based on question content)
   - Tools: ["oxytec_knowledge_search", "web_search"]
   - **MUST BE FIRST in subagent list if created**

**CREATING SUBAGENT TASKS:**

For each subagent, provide:

1. **task** (string): Multi-paragraph description with:
   ```
   Subagent: [Name]

   Objective: [Narrow scope - what to investigate]

   Questions to answer:
   - [Specific question 1 with expected format]
   - [Specific question 2 with units/calculations needed]
   - [Question 3 with risk classification requirement]

   Method hints:
   - [Calculation methods, standard values to use]
   - [Databases/sources to cite: PubChem, NIST, etc.]
   - [Risk classification: CRITICAL (>80%), HIGH (30-80%), MEDIUM (10-30%), LOW (<10%)]
   - [Mitigation requirement: propose solutions for each challenge]

   Context from extraction/enrichment:
   - [Mention data gaps from extraction_notes/data_uncertainties]
   - [Mention assumptions made: "O₂ assumed 21%", "Temperature estimated"]
   - [Instruct how to handle uncertainty: "Quantify ±X% impact on results"]

   Deliverables:
   - [Table/list format with columns specified]
   - [Risk classification table if applicable]
   - [Prioritized recommendations]

   Dependencies: INDEPENDENT (or specify if dependent on another subagent)

   Tools needed: [list tool names or "none"]
   ```

2. **relevant_content** (JSON string): Extract ONLY fields needed for this subagent
   - Example: "{\"pollutant_list\": [...], \"process_parameters\": {...}}"
   - Do NOT pass entire enriched_facts.json

3. **tools** (array): ["oxytec_knowledge_search"], ["product_database"], ["web_search"], or []

**CRITICAL DATA QUALITY INSTRUCTIONS TO SUBAGENTS:**

In each subagent task description, you MUST mention:
- Which data points are measured vs. assumed
- Which uncertainties exist (from extraction_notes/data_uncertainties)
- How to quantify the impact of missing/uncertain data
- What additional measurements would reduce uncertainty

**EXAMPLE:**

Bad task instruction:
"Calculate LEL for the VOC mixture."

Good task instruction:
"Calculate LEL for the VOC mixture. NOTE: O₂ content was not measured - assumed 21% (atmospheric air). Quantify the sensitivity: If actual O₂ is 18-24%, how does LEL percentage change? If LEL calc shows >50% LEL, classify as CRITICAL risk and recommend O₂ measurement before final design."

**DO NOT:**
- Include your own risk assessments in the planning document
- Make technology recommendations ("I think NTP is better...")
- Create data_quality_issues with severity ratings (subagents do this)
- Perform calculations (subagents do this)

---

## Output Schema

{
  "enrichment_summary": "Brief summary of Phase 1 work: what was looked up, what was assumed, what remains uncertain (50-200 words)",
  "enriched_facts": {
    ... same structure as extracted_facts but with filled gaps ...
  },
  "enrichment_notes": [
    {
      "field": "pollutant_list[0].cas_number",
      "action": "looked_up | assumed | calculated | resolved_conflict",
      "source": "web_search: PubChem | standard_value | calculation | document_priority",
      "confidence": "HIGH | MEDIUM | LOW"
    }
  ],
  "data_uncertainties": [
    {
      "field": "process_parameters.oxygen_content_percent",
      "uncertainty": "±3%",
      "impact": "Affects LEL calculation (±15% impact on safety margin)"
    }
  ],
  "subagents": [
    {
      "task": "...",
      "relevant_content": "{...}",
      "tools": [...]
    }
  ],
  "reasoning": "Brief planning strategy for Phase 2: why these subagents, in this order (50-200 words)"
}
"""
```

### Step 2: Update Planner Node to Perform Enrichment

**Edit `backend/app/agents/nodes/planner.py`:**

```python
# backend/app/agents/nodes/planner.py

async def planner_node(state: GraphState) -> dict:
    """PLANNER: Enrich data and create subagent tasks."""

    from app.agents.prompts.versions import get_prompt_version
    from app.config import settings
    from app.services.web_search_service import WebSearchService

    logger.info("planner_phase_1_starting", session_id=state["session_id"])

    # Load versioned prompt
    prompt_data = get_prompt_version("planner", settings.planner_prompt_version)

    # Prepare input (extracted facts + extraction notes)
    extracted_facts = state["extracted_facts"]
    extraction_notes = extracted_facts.get("extraction_notes", [])

    # Phase 1: Data Enrichment
    # (LLM will use web_search tool for CAS lookups)

    result = await llm_service.execute_with_tools(
        prompt=prompt_data["PROMPT_TEMPLATE"].format(
            extracted_facts=json.dumps(extracted_facts, indent=2)
        ),
        system=prompt_data["SYSTEM_PROMPT"],
        tools=[
            {
                "name": "web_search",
                "description": "Search the web for CAS numbers, substance properties, etc.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        ],
        max_iterations=10  # Allow multiple CAS lookups
    )

    # Parse result
    enriched_data = json.loads(result)

    logger.info(
        "planner_completed",
        session_id=state["session_id"],
        num_subagents=len(enriched_data["subagents"]),
        enrichment_notes_count=len(enriched_data.get("enrichment_notes", []))
    )

    return {
        "enriched_facts": enriched_data["enriched_facts"],
        "subagent_definitions": enriched_data["subagents"],
        "enrichment_summary": enriched_data["enrichment_summary"]
    }
```

### Step 3: Test PLANNER v2.0.0

```bash
# Test CAS lookup
pytest tests/integration/test_planner.py::test_cas_lookup -v

# Test subagent conditional logic
pytest tests/integration/test_planner.py::test_conditional_subagents -v

# Test enrichment phase
pytest tests/integration/test_planner.py::test_enrichment -v
```

### Step 4: Update Config and Commit

```bash
# Update config
# Edit backend/app/config.py
```

```python
planner_prompt_version: str = Field(default="v2.0.0")  # Changed from v1.0.0
```

```bash
# Update CHANGELOG
cat >> docs/development/PROMPT_CHANGELOG.md << 'EOF'

## PLANNER

### v2.0.0 (2025-10-23) - BREAKING CHANGE

**Changes:**
- ADDED: Phase 1 - Data Enrichment (CAS lookup via web_search, standard assumptions, unit disambiguation)
- ADDED: Phase 2 - Refined subagent orchestration with conditional creation logic
- ADDED: enrichment_summary, enriched_facts, enrichment_notes, data_uncertainties in output
- REFINED: Pure orchestrator role - NO technology recommendations or risk assessments

**Impact:**
- Subagents now receive enriched, high-quality data
- CAS numbers automatically looked up
- Standard assumptions documented
- Conditional subagent creation (3-8 subagents based on inquiry complexity)

**Reference:** docs/architecture/agent_refactoring_instructions.md lines 188-420

**Testing:** Enrichment phase tested with 5 inquiries - all CAS lookups successful
EOF

# Commit
git add app/agents/prompts/versions/planner_v2_0_0.py
git add app/agents/nodes/planner.py
git add app/config.py
git add docs/development/PROMPT_CHANGELOG.md
git commit -m "[PROMPT][PLANNER] v2.0.0: BREAKING - Add Phase 1 enrichment, refine orchestration"
git tag prompt-planner-v2.0.0
git push origin main --tags
```

---

## Phase 4: Downstream Agents (Week 3)

### SUBAGENT v1.1.0 (MINOR)

```bash
cp subagent_v1_0_0.py subagent_v1_1_0.py
```

**Add uncertainty quantification requirements as per refactoring instructions lines 424-484.**

### RISK_ASSESSOR v2.0.0 (MAJOR)

```bash
cp risk_assessor_v1_0_0.py risk_assessor_v2_0_0.py
```

**Shift to cross-functional synthesizer role as per lines 488-684.**

### WRITER v1.1.0 (MINOR)

```bash
cp writer_v1_0_0.py writer_v1_1_0.py
```

**Add Risk Assessor priority rules as per lines 688-816.**

---

## Rollback Procedure

If issues are discovered:

```bash
# 1. Rollback config
# Edit backend/app/config.py
extractor_prompt_version = "v1.0.0"  # Rollback from v2.0.0

# 2. Restart server
uvicorn app.main:app --reload

# 3. Document rollback
cat >> docs/development/PROMPT_CHANGELOG.md << EOF

### ROLLBACK: EXTRACTOR v2.0.0 → v1.0.0 ($(date +%Y-%m-%d))
**Reason:** [Describe issue: error rate, quality problems, performance degradation]
**Resolution:** Investigating root cause in v2.0.1
EOF

# 4. Investigate
pytest tests/integration/test_extractor.py -v --pdb
```

---

## Monitoring Queries

```sql
-- Check version usage
SELECT
  agent_type,
  prompt_version,
  COUNT(*) as executions
FROM agent_outputs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, prompt_version;

-- Error rate by version
SELECT
  agent_type,
  prompt_version,
  COUNT(*) FILTER (WHERE status = 'failed') * 100.0 / COUNT(*) as error_rate_pct
FROM agent_outputs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, prompt_version;

-- Average performance
SELECT
  agent_type,
  prompt_version,
  AVG(duration_seconds) as avg_duration,
  AVG(token_usage) as avg_tokens
FROM agent_outputs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, prompt_version;
```

---

## Success Criteria

### Per Phase

**EXTRACTOR v2.0.0:**
- [ ] Prompt size reduced by ~50% (12k → 6k chars)
- [ ] extraction_notes populated for all data gaps
- [ ] data_quality_issues empty (backward compatible)
- [ ] No carcinogen detection code remains
- [ ] Tests pass
- [ ] A/B comparison shows expected behavior

**PLANNER v2.0.0:**
- [ ] CAS numbers looked up for all missing substances
- [ ] Standard assumptions documented in enrichment_notes
- [ ] Conditional subagent creation works (3-8 subagents)
- [ ] enriched_facts has higher completeness than extracted_facts
- [ ] Tests pass
- [ ] No technology recommendations in planner output

**Full Pipeline:**
- [ ] End-to-end test completes successfully
- [ ] Feasibility report quality improved (expert validation)
- [ ] Processing time unchanged (±10%)
- [ ] Token usage unchanged (±10%)
- [ ] Error rate <1%

---

## Support

**Questions?**
- See `REFACTORING_IMPLEMENTATION_SUMMARY.md` for overview
- See `AGENT_REFACTORING_ARCHITECTURE.md` for visual diagrams
- See `agent_refactoring_instructions.md` for detailed specifications

**Issues?**
- Check logs: `tail -f backend/logs/app.log`
- Query database: `SELECT * FROM agent_outputs ORDER BY created_at DESC LIMIT 10;`
- Rollback: Change config to previous version

---

## Conclusion

Follow this guide step-by-step to implement the agent refactoring. Each phase builds on the previous one, and the versioning infrastructure ensures safe rollback if issues arise.

**Key Principle:** Test thoroughly at each phase before proceeding to the next.

**Start with:** EXTRACTOR v2.0.0 (Week 1)
