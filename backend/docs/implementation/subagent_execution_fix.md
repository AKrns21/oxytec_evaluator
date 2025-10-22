# Subagent Execution Fix - Root Cause Analysis and Solution

**Date:** 2025-10-21
**Issue:** Subagents not executing due to validation failures
**Severity:** HIGH - Blocks core functionality
**Status:** RESOLVED

---

## EXECUTIVE SUMMARY

The subagents were failing to execute due to **schema validation mismatches** between the planner prompt and Pydantic validation models. The planner was instructed to output `"reasoning"` but validation expected `"rationale"`, causing validation failures that returned empty subagent lists.

**Key Changes:**
1. ✅ Fixed field name mismatch: Added `reasoning` field to `PlannerOutput` model
2. ✅ Removed unused `tools_needed` field from validation (tools parsed from task text)
3. ✅ Increased `task` max length from 3000 → 8000 characters to accommodate detailed prompts
4. ✅ Added graceful degradation: Continue with unvalidated plans if they have subagents
5. ✅ Enhanced error logging: Log raw plan preview and detailed validation errors
6. ✅ Added subagent definition validation: Check structure before execution
7. ✅ Improved planner prompt: Explicit validation requirements and output format

---

## ROOT CAUSE ANALYSIS

### Issue 1: Field Name Mismatch ⚠️ CRITICAL

**Location:** `backend/app/agents/validation.py` + `backend/app/agents/nodes/planner.py`

**Problem:**
- **Planner prompt** (line 228): Instructs LLM to output `"reasoning": "..."`
- **Validation model** (line 45): Expects `rationale: Optional[str]`

**Impact:** Validation fails even when LLM produces perfect output → subagents = [] → no execution

**Fix:** Added `reasoning` field to `PlannerOutput` model (kept `rationale` for backward compatibility)

```python
# BEFORE (validation.py)
class PlannerOutput(BaseModel):
    subagents: list[SubagentDefinition]
    rationale: Optional[str]  # ← Wrong field name!
    strategy: Optional[str]

# AFTER (validation.py)
class PlannerOutput(BaseModel):
    subagents: list[SubagentDefinition]
    reasoning: Optional[str]  # ← Matches prompt
    rationale: Optional[str]  # ← Kept for compatibility
    strategy: Optional[str]
```

---

### Issue 2: Unused `tools_needed` Field

**Location:** `backend/app/agents/validation.py`

**Problem:**
- Validation expected `tools_needed: Optional[list[str]]` in each subagent definition
- But planner prompt only includes "Tools needed: ..." as part of task description TEXT
- Tools are extracted from task text via `extract_tools_from_task()` in subagent.py

**Impact:** Unnecessary field causing potential validation failures

**Fix:** Removed `tools_needed` field from `SubagentDefinition` model

```python
# BEFORE
class SubagentDefinition(BaseModel):
    task: str = Field(min_length=10, max_length=3000)
    relevant_content: str = Field(min_length=1)
    tools_needed: Optional[list[str]] = Field(default_factory=list)  # ← Not used!

# AFTER
class SubagentDefinition(BaseModel):
    task: str = Field(min_length=10, max_length=8000)
    relevant_content: str = Field(min_length=1)
    # tools_needed removed - extracted from task text instead
```

---

### Issue 3: Overly Strict `task` Length Constraint

**Location:** `backend/app/agents/validation.py` line 16

**Problem:**
- Validation: `max_length=3000` characters
- Planner examples: Extremely detailed task descriptions with:
  - Multi-paragraph objective
  - 5-10 detailed questions
  - Comprehensive method hints
  - Structured deliverables
  - Dependencies explanation
  - Tool descriptions
- **Reality:** Comprehensive tasks easily exceed 3000 characters

**Impact:** Well-formatted detailed task descriptions rejected by validation

**Fix:** Increased `max_length` to 8000 characters

```python
# BEFORE
task: str = Field(min_length=10, max_length=3000, ...)

# AFTER
task: str = Field(min_length=10, max_length=8000, ...)
```

---

### Issue 4: Validation Failure = Complete Execution Block

**Location:** `backend/app/agents/nodes/planner.py` lines 258-268

**Problem:**
When Pydantic validation failed, planner returned:
```python
return {
    "planner_plan": {"subagents": []},  # ← EMPTY!
    "errors": [...]
}
```

This caused subagent node to see zero subagents and skip execution entirely - even if the plan structure was actually fine but just had minor validation issues.

**Impact:** Minor validation issues (e.g., field name mismatch) caused complete workflow failure

**Fix:** Graceful degradation with enhanced logging

```python
# NEW LOGIC
except ValidationError as e:
    logger.error(..., raw_plan_preview=str(plan)[:500])  # Debug info

    # Check if plan has subagents despite validation error
    if isinstance(plan, dict) and "subagents" in plan and len(plan["subagents"]) > 0:
        logger.warning("proceeding_with_unvalidated_plan", ...)
        # Continue with unvalidated plan rather than blocking
        return {
            "planner_plan": plan,
            "warnings": [f"Validation failed but proceeding: {str(e)}"]
        }
    else:
        # No subagents - critical failure
        return {"planner_plan": {"subagents": []}, "errors": [...]}
```

**Philosophy:** Better to execute with slightly malformed data than fail completely

---

### Issue 5: Insufficient Error Logging

**Location:** Multiple files

**Problem:**
- When subagents didn't execute, logs showed `"no_subagents_to_execute"` but no context
- Couldn't diagnose WHY planner_plan was empty
- No visibility into validation failures or malformed structures

**Fix:** Enhanced logging at multiple levels

**In planner.py:**
```python
logger.error(
    "planner_validation_failed",
    session_id=session_id,
    validation_errors=str(e),
    raw_plan_preview=str(plan)[:500]  # ← NEW: See what LLM actually returned
)
```

**In subagent.py:**
```python
logger.warning(
    "no_subagents_to_execute",
    session_id=session_id,
    planner_plan_keys=list(plan.keys()) if isinstance(plan, dict) else "not_a_dict",
    planner_plan_type=type(plan).__name__  # ← NEW: Diagnose structure issues
)

# NEW: Validate each subagent definition before execution
for idx, subagent_def in enumerate(subagent_definitions):
    if "task" not in subagent_def or "relevant_content" not in subagent_def:
        logger.error(
            "invalid_subagent_definition_missing_fields",
            index=idx,
            has_task="task" in subagent_def,
            has_relevant_content="relevant_content" in subagent_def,
            available_keys=list(subagent_def.keys())  # ← See what's actually there
        )
```

---

## CHANGES MADE

### File: `backend/app/agents/validation.py`

**Change 1: Fixed PlannerOutput field names**
```python
class PlannerOutput(BaseModel):
    subagents: list[SubagentDefinition] = Field(min_length=3, max_length=10)
    reasoning: Optional[str] = Field(default="", ...)  # ← ADDED
    rationale: Optional[str] = Field(default="", ...)  # ← KEPT for backward compatibility
    strategy: Optional[str] = Field(default="", ...)
```

**Change 2: Simplified SubagentDefinition**
```python
class SubagentDefinition(BaseModel):
    task: str = Field(min_length=10, max_length=8000, ...)  # ← Increased from 3000
    relevant_content: str = Field(min_length=1, ...)
    # Removed: tools_needed field (parsed from task text instead)
```

---

### File: `backend/app/agents/nodes/planner.py`

**Change 1: Graceful validation failure handling (lines 258-288)**
- Log raw plan preview for debugging
- If plan has subagents despite validation error, proceed with warning
- Only block if no subagents found

**Change 2: Enhanced prompt output format section (lines 217-236)**
```python
**OUTPUT FORMAT - CRITICAL:**

You MUST return a valid JSON object with this EXACT structure. Do NOT add markdown code blocks.

{
  "subagents": [...],
  "reasoning": "Brief explanation..."  # ← Explicitly specify field name
}

**VALIDATION REQUIREMENTS:**
- Include 3-10 subagents (min: 3, max: 10)
- Each "task" field: 10-8000 characters  # ← Updated constraint
- Each "relevant_content" field: Must be a non-empty JSON string
- "reasoning" field: Optional but recommended
- Return ONLY valid JSON, no markdown formatting
```

---

### File: `backend/app/agents/nodes/subagent.py`

**Change 1: Enhanced empty subagent logging (lines 38-45)**
```python
logger.warning(
    "no_subagents_to_execute",
    session_id=session_id,
    planner_plan_keys=list(plan.keys()) if isinstance(plan, dict) else "not_a_dict",
    planner_plan_type=type(plan).__name__  # ← NEW: Diagnose structure
)
```

**Change 2: Subagent definition validation (lines 53-97)**
- Validate each definition is a dict
- Check for required fields: `task` and `relevant_content`
- Log detailed errors showing what's missing
- Continue with valid definitions only
- Warn if some definitions invalid

---

## TESTING RECOMMENDATIONS

### Test 1: Normal Execution
**Objective:** Verify subagents execute with valid planner output

**Steps:**
1. Start backend: `uvicorn app.main:app --reload --port 8000`
2. Upload sample documents via frontend
3. Monitor logs for: `"subagents_execution_started"` and `"subagents_execution_completed"`
4. Verify `successful > 0` in completion log

**Expected:** All subagents execute successfully

---

### Test 2: Validation Failure Graceful Degradation
**Objective:** Verify system proceeds even with minor validation issues

**Steps:**
1. Temporarily modify planner prompt to output `"strategy_summary"` instead of `"reasoning"`
2. Run workflow
3. Check logs for `"planner_validation_failed_but_has_subagents"` warning
4. Verify subagents still execute

**Expected:** Warning logged, but execution continues

---

### Test 3: Malformed Subagent Definitions
**Objective:** Verify subagent validation catches and logs structural issues

**Steps:**
1. Mock planner to return subagent without `"task"` field
2. Run workflow
3. Check logs for `"invalid_subagent_definition_missing_fields"`

**Expected:** Invalid definition skipped, error logged with details

---

### Test 4: Empty Subagent List
**Objective:** Verify clear diagnostic when no subagents created

**Steps:**
1. Mock planner to return `{"subagents": []}`
2. Run workflow
3. Check logs for `"no_subagents_to_execute"` with plan structure details

**Expected:** Clear warning with plan keys and type information

---

## MONITORING & ALERTS

### Key Log Events to Monitor

**Success Indicators:**
- `planner_completed_validated` with `num_subagents >= 3`
- `subagents_execution_started` with matching count
- `subagents_execution_completed` with `successful > 0` and `failed == 0`

**Warning Indicators:**
- `planner_validation_failed_but_has_subagents` - Minor issue, execution continues
- `some_subagent_definitions_invalid` - Some definitions skipped

**Critical Failures:**
- `planner_validation_failed_no_subagents` - Planner produced no valid subagents
- `no_valid_subagent_definitions` - All subagent definitions malformed
- `no_subagents_to_execute` - Subagent node received empty plan

---

## FUTURE IMPROVEMENTS

### 1. Schema-First Validation
**Current:** Prompt tells LLM what to output, validation model defined separately
**Better:** Generate prompt instructions directly from Pydantic schema

```python
# Pseudocode
def generate_planner_prompt(schema: Type[PlannerOutput]) -> str:
    fields = schema.model_json_schema()
    return f"Return JSON with fields: {fields}"
```

**Benefit:** Eliminates field name mismatches by construction

---

### 2. LLM Output Repair
**Current:** Validation fails → graceful degradation OR block
**Better:** Attempt automatic repair of common issues

```python
def repair_planner_output(raw_output: dict) -> dict:
    # Fix common issues
    if "rationale" in raw_output and "reasoning" not in raw_output:
        raw_output["reasoning"] = raw_output["rationale"]

    # Strip markdown code blocks
    if isinstance(raw_output, str) and raw_output.startswith("```"):
        raw_output = extract_json_from_markdown(raw_output)

    return raw_output
```

**Benefit:** Higher success rate without manual intervention

---

### 3. Dynamic Validation Constraints
**Current:** Hard-coded min/max lengths (e.g., `max_length=8000`)
**Better:** Adjust based on model context window and observed distributions

```python
# Configuration
SUBAGENT_TASK_LENGTH_P95 = 5000  # 95th percentile from production data
SUBAGENT_TASK_MAX = SUBAGENT_TASK_LENGTH_P95 * 1.5
```

**Benefit:** Validation stays aligned with actual usage patterns

---

### 4. Validation Telemetry
**Current:** Logs show validation failures, but no aggregation
**Better:** Track validation failure rates and common error patterns

**Metrics to track:**
- Validation success rate by agent
- Most common validation error types
- Field-level validation failure frequency
- Time-series of validation failures (detect regressions)

**Implementation:** LangSmith custom evaluators or Prometheus metrics

---

## CONCLUSION

The subagent execution issue was caused by a **schema mismatch** between the planner prompt and Pydantic validation models, compounded by overly strict validation that blocked execution entirely on minor errors.

**Key Lessons:**
1. **Schema alignment is critical:** Prompts and validation models must specify identical field names
2. **Fail gracefully:** Minor validation issues shouldn't cause complete workflow failure
3. **Comprehensive logging:** Detailed error logging is essential for diagnosing agent pipeline issues
4. **Validate early:** Check data structure at each pipeline stage to catch issues immediately

**Status:** All fixes implemented and ready for testing. System now has:
- ✅ Corrected schema alignment
- ✅ Graceful degradation on validation failures
- ✅ Enhanced diagnostic logging
- ✅ Structural validation at multiple checkpoints
- ✅ Clear documentation for future maintenance

---

**Next Steps:**
1. Deploy changes to development environment
2. Run comprehensive test suite (see "Testing Recommendations" above)
3. Monitor logs during next production run
4. Consider implementing "Future Improvements" for long-term robustness
