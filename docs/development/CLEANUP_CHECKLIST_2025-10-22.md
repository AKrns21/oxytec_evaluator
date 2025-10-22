# Codebase Cleanup Checklist

## Quick Reference Summary

**Total Issues Found**: 10 major categories
**Critical Issues**: 3 (orphaned directories, unused files)
**Medium Issues**: 3 (large modules, documentation, test coverage)
**Low Issues**: 4 (patterns, dependencies, config, typing)

---

## Critical Cleanup Tasks

### Task 1: Remove Orphaned Directories [15 mins]

```bash
# Navigate to repo root
cd /Users/Andreas_1_2/Dropbox/Zantor/Oxytec/Industrieanfragen/Repository_Evaluator

# Remove 4 empty orphaned directories
rm -rf backend/app/agents/{nodes}
rm -rf backend/app/api/{routes}
rm -rf backend/app/db/{migrations}
rm -rf frontend/components/{ui}
rm -rf frontend/app/upload

# Verify they're gone
git status
```

**Impact**: Removes visual clutter, no functional impact

---

### Task 2: Evaluate Unused Utility Files [30 mins]

**Files in question**:
- `backend/app/utils/cas_validator.py` (197 lines)
- `backend/app/utils/extraction_quality_validator.py` (297 lines)

**Investigation steps**:

```bash
cd backend

# Check if cas_validator is actually used anywhere
grep -r "validate_cas_checksum\|validate_and_correct_cas\|CasValidator" --include="*.py" .

# Check if extraction_quality_validator is actually used anywhere
grep -r "validate_extracted_facts" --include="*.py" .

# If no results from above, both files are DEAD CODE
```

**Expected findings**:
- `cas_validator.py` - only imported by extraction_quality_validator.py
- `extraction_quality_validator.py` - imported in extractor.py but function never called

**Decision**:
- If functions are not called: DELETE both files
- If functions are called: KEEP and integrate into workflow

---

## Medium Priority Tasks

### Task 3: Check for Unused Imports [30 mins]

```bash
cd backend

# Run Ruff to find unused imports
ruff check app/ --select=F401

# Review each finding and remove if confirmed unused
```

**Common patterns to remove**:
- Unused imports in test files
- Commented-out code
- Debug imports

---

### Task 4: Identify Large Files for Refactoring [1 hour analysis]

**Files to refactor** (in priority order):

1. **`backend/app/agents/nodes/subagent.py`** (690 lines)
   - **Issues**: 
     - Mixes concern: subagent orchestration + execution + prompt building
     - Hard to test individual parts
   - **Refactor into**:
     - `subagent_executor.py` - execute single subagent
     - `subagent_coordinator.py` - manage parallel execution
     - `subagent_prompt.py` - build subagent prompts

2. **`backend/app/agents/nodes/extractor.py`** (668 lines)
   - **Issues**: 
     - Mixes: extraction + validation + data cleaning
     - Multiple helper functions in single file
   - **Refactor into**:
     - Extract `normalize_units()` and `clean_extracted_data()` to `data_cleaning.py`
     - Keep extraction logic in extractor.py

3. **`backend/app/services/document_service.py`** (677 lines)
   - **Issues**: 
     - Large conditional for multiple formats (PDF, DOCX, Excel, image)
     - Each format has different logic
   - **Consider**:
     - Extract format handlers: `pdf_handler.py`, `docx_handler.py`, etc.
     - Create factory pattern for format selection

---

## Quality Improvement Tasks

### Task 5: Add Missing Tests [2-4 hours]

**Create these test files**:

```bash
# Unit tests for services
touch backend/tests/unit/test_rag_service.py
touch backend/tests/unit/test_technology_rag_service.py
touch backend/tests/unit/test_llm_service.py
touch backend/tests/unit/test_embedding_service.py
touch backend/tests/unit/test_document_service.py

# Integration tests
touch backend/tests/integration/test_agent_graph.py
touch backend/tests/integration/test_api_endpoints.py

# Add to pytest
cd backend
python3 -m pytest tests/ -v --cov=app
```

**Target coverage**: Aim for 50%+ for critical modules

---

### Task 6: Consolidate Documentation [1-2 hours]

**Current fragmentation**:
- `CLAUDE.md` - comprehensive guidelines
- `README.md` - project overview
- `docs/` - architecture, development, evaluation
- `backend/docs/` - setup, implementation, API
- `backend/tests/README.md` - test docs

**Consolidation plan**:

1. **Keep as-is** (don't touch):
   - `CLAUDE.md` (AI assistant instructions)
   - `README.md` (project overview)
   - `backend/docs/setup/` (setup guides - well organized)

2. **Archive old files**:
   - Move `backend/docs/implementation/*.md` older than 2025-10-15 to `backend/docs/archive/`
   - Keep only latest: CHANGES_SUMMARY_2025-10-21.md, CUSTOMER_QUESTIONS_STRATEGY.md

3. **Create unified documentation**:
   - Add `backend/docs/api/ENDPOINTS.md` - comprehensive API reference
   - Update `docs/README.md` with pointers to key docs

---

## Verification Checklist

After cleanup, verify:

- [ ] All tests pass: `pytest tests/ -v`
- [ ] No import errors: `python3 -c "from app import *"`
- [ ] No ruff warnings: `ruff check app/ --select=F401,E501`
- [ ] App still starts: `uvicorn app.main:app --reload`
- [ ] Frontend builds: `npm run build`
- [ ] No git conflicts: `git status`

---

## Estimated Time & Impact

| Task | Time | Difficulty | Priority |
|------|------|-----------|----------|
| Remove orphaned dirs | 15 min | Easy | HIGH |
| Evaluate unused files | 30 min | Medium | HIGH |
| Check unused imports | 30 min | Easy | MEDIUM |
| Refactor large files | 6-8 hrs | Hard | MEDIUM |
| Add tests | 4-6 hrs | Medium | MEDIUM |
| Consolidate docs | 2-3 hrs | Easy | LOW |

**Quick Wins** (under 1 hour):
- Remove orphaned directories
- Check unused files
- Run ruff checks

**Total estimated for all**: 12-18 hours of focused work

---

## File Locations Quick Reference

**Orphaned directories** (delete):
```
backend/app/agents/{nodes}/
backend/app/api/{routes}/
backend/app/db/{migrations}/
frontend/components/{ui}/
frontend/app/upload/
```

**Potentially unused** (investigate):
```
backend/app/utils/cas_validator.py
backend/app/utils/extraction_quality_validator.py
```

**Large modules** (refactor):
```
backend/app/agents/nodes/subagent.py (690 lines)
backend/app/agents/nodes/extractor.py (668 lines)
backend/app/services/document_service.py (677 lines)
```

**Documentation to consolidate**:
```
backend/docs/implementation/  [archive old files]
docs/README.md               [consolidate pointers]
backend/docs/api/            [create if not exists]
```

---

## Success Criteria

After cleanup, the codebase should:

1. ✅ Have no orphaned/empty directories
2. ✅ Have no dead/unused code
3. ✅ Have all imports used (ruff F401 passes)
4. ✅ Have 50%+ test coverage for critical modules
5. ✅ Have consolidated documentation
6. ✅ Have no merge conflicts
7. ✅ Pass all existing tests
8. ✅ Start without errors

---

## References

- Full analysis: `docs/development/CODEBASE_STRUCTURE_ANALYSIS_2025-10-22.md`
- Project instructions: `CLAUDE.md`
- Backend docs: `backend/docs/README.md`
- Test framework: `backend/tests/README.md`

