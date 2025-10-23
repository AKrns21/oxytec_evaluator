# Prompt Versioning System - Implementation Summary

**Date:** 2025-10-23
**Status:** Phase 1 (Internal Solution) - PARTIALLY IMPLEMENTED
**Completion:** ~60% (Core infrastructure complete, agent refactoring in progress)

---

## Overview

Implemented an internal prompt versioning system for the Oxytec Multi-Agent Feasibility Platform to enable systematic tracking, A/B testing, and evolution of agent prompts during engineer feedback loops.

## What Was Implemented

### ✅ 1. Prompt Version Directory Structure

**Created:** `backend/app/agents/prompts/versions/`

**Contents:**
- `__init__.py` - Prompt version loader with `get_prompt_version()` and `list_available_versions()` functions
- `extractor_v1_0_0.py` - Baseline EXTRACTOR prompt (19,314 chars)
- `planner_v1_0_0.py` - Baseline PLANNER prompt (8,073 chars)
- `writer_v1_0_0.py` - Baseline WRITER prompt (20,007 chars)
- `risk_assessor_v1_0_0.py` - Baseline RISK_ASSESSOR prompt (15,200 chars)
- `subagent_v1_0_0.py` - Baseline SUBAGENT prompt (manually created)

**File Structure:**
```
backend/app/agents/prompts/versions/
├── __init__.py                 # Version loader utilities
├── extractor_v1_0_0.py        # Extractor v1.0.0
├── planner_v1_0_0.py          # Planner v1.0.0
├── writer_v1_0_0.py           # Writer v1.0.0
├── risk_assessor_v1_0_0.py    # Risk Assessor v1.0.0
└── subagent_v1_0_0.py         # Subagent v1.0.0
```

**Version File Format:**
```python
VERSION = "v1.0.0"
CHANGELOG = """v1.0.0 - Description of changes"""
SYSTEM_PROMPT = """System instruction..."""
PROMPT_TEMPLATE = """Main prompt with {placeholders}..."""
```

---

### ✅ 2. Database Schema Update

**Added Column:** `agent_outputs.prompt_version VARCHAR(20) NULL`

**Purpose:** Links each agent output to the exact prompt version used, enabling traceability from report → prompt version.

**Migration Script:** `backend/scripts/migrations/add_prompt_version_column.py`

**Run Migration:**
```bash
cd backend
source .venv/bin/activate
python3 scripts/migrations/add_prompt_version_column.py
```

**Rollback:**
```bash
python3 scripts/migrations/add_prompt_version_column.py rollback
```

**Migration Status:** ✅ Successfully applied to Supabase database

---

### ✅ 3. Configuration Management

**Added to `backend/app/config.py`:**
```python
# Prompt versioning configuration
extractor_prompt_version: str = "v1.0.0"
planner_prompt_version: str = "v1.0.0"
subagent_prompt_version: str = "v1.0.0"
risk_assessor_prompt_version: str = "v1.0.0"
writer_prompt_version: str = "v1.0.0"
```

**Environment Variables:** Can be overridden via `.env`:
```bash
EXTRACTOR_PROMPT_VERSION=v1.1.0
WRITER_PROMPT_VERSION=v1.2.0
```

**A/B Testing:** Change config values to test different prompt versions on same inquiry.

---

### ✅ 4. Agent Node Refactoring

**Status:** 1/5 nodes refactored

**Completed:**
- ✅ **EXTRACTOR** (`app/agents/nodes/extractor.py`) - Fully refactored to use versioned prompts

**Refactoring Pattern:**
```python
# Import version loader
from app.agents.prompts.versions import get_prompt_version
from app.config import settings

# Load versioned prompt
prompt_data = get_prompt_version("extractor", settings.extractor_prompt_version)
prompt_template = prompt_data["PROMPT_TEMPLATE"]
system_prompt = prompt_data["SYSTEM_PROMPT"]

# Format with runtime data
extraction_prompt = prompt_template.format(
    CARCINOGEN_DATABASE=CARCINOGEN_DATABASE,
    combined_text=combined_text
)

# Use in LLM call
await llm_service.execute_structured(
    prompt=extraction_prompt,
    system_prompt=system_prompt,  # Use versioned system prompt
    ...
)
```

**Pending Refactoring:**
- ⏳ **PLANNER** - Needs refactoring (estimated: 20 min)
- ⏳ **WRITER** - Needs refactoring (estimated: 20 min)
- ⏳ **RISK_ASSESSOR** - Needs refactoring (estimated: 20 min)
- ⏳ **SUBAGENT** - Needs refactoring (estimated: 25 min, more complex due to dynamic prompt building)

---

### ⏳ 5. Database Logging Integration (PENDING)

**Required:** Update agent nodes to pass `prompt_version` when logging to `agent_outputs` table.

**Implementation Pattern:**
```python
# In each agent node, after execution:
agent_output = AgentOutput(
    session_id=session_id,
    agent_type="extractor",
    content={"result": extracted_facts},
    tokens_used=tokens,
    duration_ms=duration,
    prompt_version=settings.extractor_prompt_version  # ADD THIS
)
```

**Status:** Not yet implemented (requires 30-45 min to update all logging calls)

---

### ✅ 6. Documentation

**Created:**
- `docs/development/PROMPT_CHANGELOG.md` (template created, needs population)
- `docs/development/PROMPT_VERSIONING_IMPLEMENTATION_SUMMARY.md` (this document)

**Pending:**
- Populate `PROMPT_CHANGELOG.md` with v1.0.0 baseline entries
- Add versioning workflow to `CLAUDE.md`

---

## Usage Instructions

### Creating a New Prompt Version

**Example: Update EXTRACTOR prompt (v1.0.0 → v1.1.0)**

1. **Copy existing version:**
   ```bash
   cd backend/app/agents/prompts/versions
   cp extractor_v1_0_0.py extractor_v1_1_0.py
   ```

2. **Edit new version:**
   ```python
   # extractor_v1_1_0.py
   VERSION = "v1.1.0"

   CHANGELOG = """
   v1.1.0 (2025-10-24) - Improve carcinogen detection
   - Added benzene detection patterns
   - Enhanced formaldehyde flagging logic
   - Improved CAS number extraction from German SDS format
   """

   PROMPT_TEMPLATE = """... updated prompt text ..."""
   ```

3. **Update configuration:**
   ```python
   # backend/app/config.py
   extractor_prompt_version: str = "v1.1.0"  # Change from v1.0.0
   ```

4. **Document changes:**
   ```markdown
   # docs/development/PROMPT_CHANGELOG.md

   ## EXTRACTOR Agent

   ### v1.1.0 (2025-10-24)
   **Type:** Minor
   **Changes:**
   - Added benzene detection patterns
   - Enhanced formaldehyde flagging logic
   - Improved CAS number extraction

   **Rationale:** Engineer feedback indicated missed carcinogens in SDS Section 3
   **Testing:** Tested on ACO_Styrol_SDS.pdf, correctly detects benzene at 40-60%
   ```

5. **Test new version:**
   ```bash
   # Run test inquiry with new prompt
   pytest tests/integration/test_extractor.py -k test_sds_extraction
   ```

6. **Commit changes:**
   ```bash
   git add app/agents/prompts/versions/extractor_v1_1_0.py app/config.py docs/development/PROMPT_CHANGELOG.md
   git commit -m "[PROMPT][EXTRACTOR] v1.1.0: Improve carcinogen detection"
   git tag prompt-extractor-v1.1.0
   ```

---

### A/B Testing Prompts

**Scenario:** Test WRITER v1.0.0 vs. v1.1.0 on same inquiry

1. **Run with v1.0.0:**
   ```bash
   # backend/.env
   WRITER_PROMPT_VERSION=v1.0.0

   # Upload files, save session_id
   curl -X POST http://localhost:8000/api/sessions/create
   # Result: session_id = abc-123
   ```

2. **Run with v1.1.0:**
   ```bash
   # backend/.env
   WRITER_PROMPT_VERSION=v1.1.0

   # Upload same files again
   curl -X POST http://localhost:8000/api/sessions/create
   # Result: session_id = def-456
   ```

3. **Compare outputs:**
   ```bash
   # Query database
   SELECT session_id, prompt_version, content
   FROM agent_outputs
   WHERE agent_type = 'writer'
   AND session_id IN ('abc-123', 'def-456');
   ```

4. **Share with engineers:**
   - Export both reports to PDF
   - Label: "Report A (Writer v1.0.0)" vs. "Report B (Writer v1.1.0)"
   - Collect feedback on quality, accuracy, tone

---

### Checking Which Version Generated a Report

**Query prompt version for a session:**
```sql
SELECT
    agent_type,
    prompt_version,
    created_at
FROM agent_outputs
WHERE session_id = 'abc-123'
ORDER BY created_at;
```

**Expected Output:**
```
agent_type     | prompt_version | created_at
---------------|----------------|----------------------------
extractor      | v1.0.0         | 2025-10-23 10:15:23
planner        | v1.0.0         | 2025-10-23 10:15:28
subagent       | v1.0.0         | 2025-10-23 10:15:45
risk_assessor  | v1.0.0         | 2025-10-23 10:15:50
writer         | v1.1.0         | 2025-10-23 10:16:05
```

---

### Listing Available Versions

**Python API:**
```python
from app.agents.prompts.versions import list_available_versions

versions = list_available_versions("extractor")
print(versions)  # ['v1.2.0', 'v1.1.0', 'v1.0.0'] (sorted descending)
```

**Manual check:**
```bash
ls backend/app/agents/prompts/versions/extractor_*.py
# Output:
# extractor_v1_0_0.py
# extractor_v1_1_0.py
```

---

## Next Steps

### Immediate (Complete Phase 1)

**Estimated Time:** 2-3 hours

1. **Refactor remaining agent nodes** (1.5 hours):
   - ⏳ PLANNER node → Load from `planner_v1_0_0.py`
   - ⏳ WRITER node → Load from `writer_v1_0_0.py`
   - ⏳ RISK_ASSESSOR node → Load from `risk_assessor_v1_0_0.py`
   - ⏳ SUBAGENT node → Load from `subagent_v1_0_0.py` (dynamic prompt building requires special handling)

2. **Add database logging for prompt_version** (45 min):
   - Update all agent nodes to pass `prompt_version` to `AgentOutput` creation
   - Update `app/api/routes/sessions.py` to log prompt versions in `agent_outputs` table

3. **Testing** (30 min):
   - Run full workflow test: Upload inquiry → Generate report
   - Verify all 5 agents log prompt versions to database
   - Query `agent_outputs` table to confirm version tracking works

4. **Documentation** (15 min):
   - Populate `PROMPT_CHANGELOG.md` with v1.0.0 baseline entries for all 5 agents
   - Add versioning workflow section to `CLAUDE.md`

---

### Short-term (Engineer Feedback Integration)

**Timeline:** During first feedback cycle (2-4 weeks)

1. **Create v1.1.0 versions based on feedback:**
   - Example: Engineers report WRITER generates too-optimistic "Positive Faktoren"
   - Action: Create `writer_v1_1_0.py` with stricter filtering instructions
   - Test: A/B compare v1.0.0 vs. v1.1.0 on 5 inquiries

2. **Establish versioning workflow:**
   - **Feedback format:** Engineers annotate reports with section-specific feedback
   - **Triage:** Map feedback to specific agent (e.g., "Handlungsempfehlungen too generic" → WRITER or RISK_ASSESSOR)
   - **Iteration:** Create new prompt version, test, deploy

3. **Track prompt performance metrics:**
   - **Engineer satisfaction score** (1-5) per report section
   - **Revision requests** (% of reports requiring manual editing)
   - **Time to approval** (hours from generation to engineer sign-off)

---

### Long-term (External Platform Migration - Optional)

**Timeline:** If feedback volume >10 experiments/week

**Trigger conditions:**
- Running >10 prompt experiments per week
- Need for non-technical stakeholders to edit prompts
- Desire for visual dashboards showing prompt performance

**Recommended platform:** **LangSmith Prompts** (already using LangSmith for tracing)

**Migration steps:**
1. Export v1.x.y prompts from Python files to LangSmith UI
2. Update `get_prompt_version()` to fetch from LangSmith API instead of local files
3. Keep database `prompt_version` tracking (unchanged)
4. Benefit: Visual prompt editor, built-in A/B testing dashboard, collaborative feedback

**Effort:** 4-6 hours migration + training

---

## File Structure (Current State)

```
backend/
├── app/
│   ├── agents/
│   │   ├── nodes/
│   │   │   ├── extractor.py         ✅ Refactored (uses versioned prompts)
│   │   │   ├── planner.py           ⏳ Pending refactoring
│   │   │   ├── writer.py            ⏳ Pending refactoring
│   │   │   ├── risk_assessor.py     ⏳ Pending refactoring
│   │   │   └── subagent.py          ⏳ Pending refactoring
│   │   ├── prompts/
│   │   │   ├── __init__.py          (shared fragments: CARCINOGEN_DATABASE, etc.)
│   │   │   └── versions/
│   │   │       ├── __init__.py                ✅ Implemented (loader utilities)
│   │   │       ├── extractor_v1_0_0.py        ✅ Created (baseline)
│   │   │       ├── planner_v1_0_0.py          ✅ Created (baseline)
│   │   │       ├── writer_v1_0_0.py           ✅ Created (baseline)
│   │   │       ├── risk_assessor_v1_0_0.py    ✅ Created (baseline)
│   │   │       └── subagent_v1_0_0.py         ✅ Created (baseline)
│   ├── config.py                    ✅ Updated (added prompt version configs)
│   ├── models/
│   │   └── database.py              ✅ Updated (added prompt_version column)
├── scripts/
│   ├── migrations/
│   │   └── add_prompt_version_column.py       ✅ Created & executed
│   └── extract_prompts.py           ✅ Created (automated extraction tool)
└── docs/
    └── development/
        ├── PROMPT_CHANGELOG.md                ✅ Created (template)
        └── PROMPT_VERSIONING_IMPLEMENTATION_SUMMARY.md  ✅ Created (this doc)
```

---

## Key Benefits

### 1. **Traceability**
- **Problem:** "This report has incorrect risk assessment. Which prompt version generated it?"
- **Solution:** Query `agent_outputs.prompt_version` by `session_id`

### 2. **A/B Testing**
- **Problem:** "Does adding explicit cost disclaimer improve engineer satisfaction?"
- **Solution:** Test WRITER v1.0.0 vs. v1.1.0 on 5 inquiries, compare feedback scores

### 3. **Rollback Safety**
- **Problem:** "New EXTRACTOR prompt breaks CAS number extraction"
- **Solution:** `EXTRACTOR_PROMPT_VERSION=v1.0.0` in `.env` → instant rollback

### 4. **Collaboration**
- **Problem:** "Engineers want to suggest prompt improvements but can't edit Python code"
- **Solution:** Version files are plain text → engineers can draft improvements in Markdown, developers implement as v1.x.y

### 5. **Audit Trail**
- **Problem:** "Why did we change the WRITER prompt in October?"
- **Solution:** `git log docs/development/PROMPT_CHANGELOG.md` shows rationale, testing results, feedback scores

---

## Known Limitations

### 1. **Subagent Prompts Are Dynamic**
- **Issue:** SUBAGENT builds prompts dynamically with runtime data (task description, relevant_content)
- **Workaround:** Version file contains template with `{task_description}` and `{relevant_content}` placeholders
- **Impact:** Slightly more complex refactoring (estimated +10 min)

### 2. **Shared Prompt Fragments**
- **Issue:** `CARCINOGEN_DATABASE`, `POSITIVE_FACTORS_FILTER` defined in `app/agents/prompts.py`, not versioned
- **Decision:** Keep shared fragments unversioned for now (they're referenced by all agents)
- **Future:** If fragments evolve, create `fragments_v1_0_0.py` with versioned fragments

### 3. **No Automated Version Bumping**
- **Issue:** Manual process to create `extractor_v1_1_0.py` and update `config.py`
- **Future:** Could create CLI tool: `python3 scripts/bump_prompt.py extractor minor`

### 4. **Database Migration Required for New Deployments**
- **Issue:** Fresh database installs need migration script
- **Solution:** Run `python3 scripts/migrations/add_prompt_version_column.py` during setup
- **Future:** Add to `backend/docs/setup/DATABASE_SETUP.md`

---

## Testing Recommendations

### Unit Tests (for version loader)
```python
# tests/unit/test_prompt_versioning.py
def test_get_prompt_version():
    data = get_prompt_version("extractor", "v1.0.0")
    assert data["VERSION"] == "v1.0.0"
    assert "PROMPT_TEMPLATE" in data
    assert "SYSTEM_PROMPT" in data

def test_list_available_versions():
    versions = list_available_versions("extractor")
    assert "v1.0.0" in versions
    assert versions == sorted(versions, reverse=True)  # Descending order
```

### Integration Tests (for agent refactoring)
```python
# tests/integration/test_extractor_versioning.py
async def test_extractor_uses_configured_version():
    """Verify EXTRACTOR loads prompt from configured version."""
    # Set version in config
    settings.extractor_prompt_version = "v1.0.0"

    # Run extractor
    result = await extractor_node(state)

    # Verify version was used (check logs or output structure)
    assert result is not None
```

### E2E Tests (for full workflow)
```python
# tests/e2e/test_full_workflow_with_versioning.py
async def test_prompt_versions_logged_to_database(test_session):
    """Verify all agents log prompt versions to database."""
    session_id = test_session["id"]

    # Run full workflow
    await run_feasibility_study(session_id)

    # Query agent_outputs
    outputs = await db.query(
        "SELECT agent_type, prompt_version FROM agent_outputs WHERE session_id = $1",
        session_id
    )

    # Verify all 5 agents logged versions
    assert len(outputs) == 5
    assert all(output["prompt_version"] is not None for output in outputs)
```

---

## Rollback Plan

**If prompt versioning causes issues:**

1. **Database rollback:**
   ```bash
   python3 scripts/migrations/add_prompt_version_column.py rollback
   ```

2. **Code rollback:**
   ```bash
   git revert <commit-hash>  # Revert agent refactoring commits
   ```

3. **Config rollback:**
   ```python
   # backend/app/config.py
   # Remove prompt version configs
   ```

**Impact:** Zero - system works with or without `prompt_version` column (nullable field)

---

## Conclusion

**Phase 1 Implementation:** ~60% complete

**Core infrastructure:** ✅ Fully functional
- Versioned prompt files created
- Database schema updated
- Configuration management in place
- EXTRACTOR fully refactored as reference

**Remaining work:** ~2-3 hours
- Refactor 4 remaining agent nodes
- Add database logging integration
- Complete testing and documentation

**Ready for use:** Yes (partial)
- Can already version EXTRACTOR prompts
- Infrastructure supports adding more versioned agents incrementally

**Recommendation:** Complete remaining 4 agent node refactorings (1.5 hours) before starting engineer feedback loops to ensure full traceability from day one.
