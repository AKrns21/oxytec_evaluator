# Prompt Versions - Quick Reference

This directory contains versioned prompts for all agents in the Oxytec Multi-Agent Feasibility Platform.

## Version Control Philosophy

**Why version prompts?**
1. Track prompt evolution over time
2. Enable easy rollback if issues arise
3. A/B testing between versions
4. Clear audit trail for changes
5. Support for gradual deployment

## File Naming Convention

```
<agent_name>_v<major>_<minor>_<patch>.py
```

**Examples:**
- `extractor_v1_0_0.py` - Baseline version
- `extractor_v2_0_0.py` - Major refactoring
- `planner_v2_1_0.py` - Added new feature
- `writer_v1_0_1.py` - Bug fix

## Current Versions

### EXTRACTOR

| Version | Status | Token Count | Notes |
|---------|--------|-------------|-------|
| **v2.0.0** | ✅ Ready for testing | ~3,200 | Major refactoring: Pure technical extraction |
| v1.0.0 | 🟡 Baseline (deprecated) | ~6,500 | Original version with business logic |

**Latest:** v2.0.0 (2025-10-24)
**Documentation:** `/docs/development/EXTRACTOR_v2_APPROVAL_PACKAGE.md`

**Key Changes in v2.0.0:**
- ❌ Removed: Carcinogen detection (~1,200 tokens)
- ❌ Removed: Severity ratings (~300 tokens)
- ✅ Added: extraction_notes field (~500 tokens)
- ✅ Added: Technical cleanup rules (~400 tokens)
- **Net change:** -50% tokens

---

### PLANNER

| Version | Status | Token Count | Notes |
|---------|--------|-------------|-------|
| v1.0.0 | 🟢 Active | ~5,000 | Baseline version |

**Latest:** v1.0.0 (baseline)
**Next:** v2.0.0 (in planning - will add Phase 1 enrichment)

---

### SUBAGENT

| Version | Status | Token Count | Notes |
|---------|--------|-------------|-------|
| v1.0.0 | 🟢 Active | ~3,500 | Baseline version |

**Latest:** v1.0.0 (baseline)
**Next:** v2.0.0 (planned - uncertainty quantification enhancements)

---

### RISK_ASSESSOR

| Version | Status | Token Count | Notes |
|---------|--------|-------------|-------|
| v1.0.0 | 🟢 Active | ~4,000 | Baseline version |

**Latest:** v1.0.0 (baseline)
**Next:** v2.0.0 (planned - change to "cross-functional synthesizer" role)

---

### WRITER

| Version | Status | Token Count | Notes |
|---------|--------|-------------|-------|
| v1.0.0 | 🟢 Active | ~6,000 | Baseline version |

**Latest:** v1.0.0 (baseline)
**Next:** v1.1.0 (planned - conflict resolution protocol)

---

## How to Use

### For Developers: Switching Versions

**Option 1: Direct import (simple)**

```python
# backend/app/agents/nodes/extractor.py

from app.agents.prompts.versions.extractor_v2_0_0 import PROMPT_TEMPLATE
```

**Option 2: Feature flag (recommended for production)**

```python
# backend/app/agents/nodes/extractor.py

from app.config import settings

if settings.EXTRACTOR_PROMPT_VERSION == "v2.0.0":
    from app.agents.prompts.versions.extractor_v2_0_0 import PROMPT_TEMPLATE
else:
    from app.agents.prompts.versions.extractor_v1_0_0 import PROMPT_TEMPLATE
```

Add to `.env`:
```bash
EXTRACTOR_PROMPT_VERSION=v2.0.0  # or v1.0.0 for rollback
```

### For Prompt Engineers: Creating New Versions

**1. Copy the latest version:**
```bash
cp extractor_v2_0_0.py extractor_v2_1_0.py
```

**2. Update metadata (REQUIRED - both VERSION and CHANGELOG):**
```python
VERSION = "v2.1.0"

CHANGELOG = """
v2.1.0 (2025-XX-XX) - Brief description
- Change 1: What changed
- Change 2: Why it changed
- Change 3: Impact (tokens, performance, etc.)
- Breaking changes: Yes/No
"""
```

**⚠️ CRITICAL:** The inline `CHANGELOG` variable is displayed in the UI when users click "changelog". It MUST be updated for every version.

**3. Modify the PROMPT_TEMPLATE:**
```python
PROMPT_TEMPLATE = """
[Your updated prompt text here]
"""
```

**4. Document in centralized PROMPT_CHANGELOG.md (REQUIRED):**
Add entry to `/docs/development/PROMPT_CHANGELOG.md` following semantic versioning format.

**Why both?**
- Inline `CHANGELOG` in file → Shows in UI for users
- `/docs/development/PROMPT_CHANGELOG.md` → Project-wide audit trail for management

**5. Commit to git with descriptive message:**
```bash
git add app/agents/prompts/versions/<agent>_v<version>.py
git commit -m "feat(prompts): Add <AGENT> v<version> - <brief description>"
```

**6. Test before deploying:**
```bash
cd backend
python3 -m pytest tests/evaluation/<agent_name>/ -v
```

---

## Version Status Legend

| Status | Meaning |
|--------|---------|
| 🟢 **Active** | Currently deployed in production |
| ✅ **Ready** | Tested and approved, ready for deployment |
| 🟡 **Deprecated** | Old version, kept for rollback only |
| 🔧 **In Development** | Work in progress, not yet tested |
| ⛔ **Archived** | No longer maintained, do not use |

---

## Semantic Versioning Rules

We use **Semantic Versioning** for prompts:

### MAJOR (vX.0.0) - Breaking Changes
- Output format changes
- Required field changes
- Major behavioral shifts
- Scope changes (e.g., EXTRACTOR v2.0.0 removing business logic)

**When to bump:** Changes that require downstream agent updates

### MINOR (vX.Y.0) - New Features
- New sections added
- Significant prompt improvements
- New instructions without breaking changes
- Enhanced detection patterns

**When to bump:** Adds functionality, backward compatible

### PATCH (vX.Y.Z) - Bug Fixes
- Bug fixes
- Clarifications
- Small adjustments
- Typo corrections
- Example improvements

**When to bump:** Fixes without adding features

---

## Testing Guidelines

### Before Deploying New Version

1. **Unit Tests:**
   ```bash
   python3 -m pytest tests/unit/test_<agent>_v<version>.py -v
   ```

2. **Evaluation Tests:**
   ```bash
   python3 -m pytest tests/evaluation/<agent>/ -v
   ```

3. **Integration Tests:**
   ```bash
   python3 -m pytest tests/integration/test_<agent>_integration.py -v
   ```

4. **Manual Testing:**
   - Test with 5-10 historical cases
   - Compare outputs with previous version
   - Verify JSON parsing succeeds
   - Check field extraction accuracy

### A/B Testing in Production

**Recommended rollout:**
1. **Day 1-2:** 10% of sessions → new version
2. **Day 3-5:** 25% of sessions → new version
3. **Day 6-10:** 50% of sessions → new version
4. **Day 11+:** 100% if no issues

**Rollback triggers:**
- JSON parsing errors >1%
- Field extraction accuracy drops >5%
- Error rate increases >2%
- User complaints about quality

---

## File Structure

```
backend/app/agents/prompts/versions/
├── README.md                    # This file
├── extractor_v1_0_0.py         # EXTRACTOR baseline
├── extractor_v2_0_0.py         # EXTRACTOR refactored ✅ NEW
├── planner_v1_0_0.py           # PLANNER baseline (to be added)
├── subagent_v1_0_0.py          # SUBAGENT baseline (to be added)
├── risk_assessor_v1_0_0.py     # RISK_ASSESSOR baseline (to be added)
└── writer_v1_0_0.py            # WRITER baseline (to be added)
```

---

## Migration Path (Refactoring Project)

The Oxytec platform is undergoing a **5-agent refactoring** to separate concerns and reduce prompt bloat.

### Refactoring Timeline

**Phase 1: EXTRACTOR v2.0.0** ✅ COMPLETE
- Status: Ready for testing
- Token reduction: 50%
- Focus: Pure technical extraction, no business logic
- Approval: Pending - Andreas

**Phase 2: PLANNER v2.0.0** (Next)
- Add Phase 1: Data Enrichment (CAS lookups, unit conversions)
- Add Phase 2: Pure Orchestrator (create subagent tasks)
- Estimated: 3-4 days

**Phase 3: SUBAGENT v2.0.0**
- Add input context clarification
- Uncertainty quantification requirements
- Estimated: 1-2 days

**Phase 4: RISK_ASSESSOR v2.0.0**
- Change to "cross-functional synthesizer" role
- Remove "VETO POWER" language
- Estimated: 2-3 days

**Phase 5: WRITER v1.1.0**
- Add conflict resolution protocol
- Risk Assessor integration priority
- Estimated: 1-2 days

**Total Estimated Time:** 4-6 weeks

---

## Documentation Links

### General Documentation
- **Refactoring Instructions:** `/docs/architecture/agent_refactoring_instructions.md`
- **Prompt Changelog:** `/docs/development/PROMPT_CHANGELOG.md`
- **Project CLAUDE.md:** `/CLAUDE.md`

### EXTRACTOR v2.0.0 Documentation
- **Approval Package:** `/docs/development/EXTRACTOR_v2_APPROVAL_PACKAGE.md`
- **Implementation Summary:** `/docs/development/EXTRACTOR_v2.0.0_IMPLEMENTATION_SUMMARY.md`
- **Version Comparison:** `/docs/development/EXTRACTOR_v1_vs_v2_COMPARISON.md`

---

## FAQ

### Q: Can I use old and new versions simultaneously?

**A:** Yes, using feature flags:
```python
if session_id % 2 == 0:
    use_version = "v2.0.0"
else:
    use_version = "v1.0.0"
```

### Q: How do I roll back if new version has issues?

**A:**
1. **Immediate:** Change import to old version
2. **Feature flag:** Update environment variable
3. **Database:** No rollback needed (backward compatible)

### Q: Should I delete old versions?

**A:** No, keep for:
1. Rollback capability
2. Version comparison
3. Historical reference
4. A/B testing

Deprecate old versions but don't delete them.

### Q: How do I test a new version locally?

**A:**
```bash
cd backend
source .venv/bin/activate

# Edit the import in the node file
# OR set environment variable
export EXTRACTOR_PROMPT_VERSION=v2.0.0

# Run tests
python3 -m pytest tests/evaluation/extractor/ -v
```

---

## Contact

**Prompt Engineering Specialist:** Claude
**Project Owner:** Andreas
**Location:** `/backend/app/agents/prompts/versions/`

For questions about prompt versioning, see:
- This README
- `/docs/development/PROMPT_CHANGELOG.md`
- `/docs/architecture/agent_refactoring_instructions.md`

---

**Last Updated:** 2025-10-24
**Latest Version Added:** EXTRACTOR v2.0.0
