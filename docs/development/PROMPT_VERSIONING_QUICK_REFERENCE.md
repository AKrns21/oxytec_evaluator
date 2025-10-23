# Prompt Versioning - Quick Reference Guide

## Quick Commands

### Check Current Versions
```bash
grep "_prompt_version" backend/app/config.py
```

### Create New Version
```bash
# 1. Copy existing version
cd backend/app/agents/prompts/versions
cp extractor_v1_0_0.py extractor_v1_1_0.py

# 2. Edit new version (update VERSION, CHANGELOG, PROMPT_TEMPLATE)

# 3. Update config
# Edit backend/app/config.py: extractor_prompt_version = "v1.1.0"

# 4. Test
pytest tests/integration/test_extractor.py -v

# 5. Commit
git add app/agents/prompts/versions/extractor_v1_1_0.py app/config.py
git commit -m "[PROMPT][EXTRACTOR] v1.1.0: Description"
git tag prompt-extractor-v1.1.0
```

### A/B Test Two Versions
```bash
# Test v1.0.0
EXTRACTOR_PROMPT_VERSION=v1.0.0 python3 scripts/run_inquiry.py inquiry_001.pdf

# Test v1.1.0
EXTRACTOR_PROMPT_VERSION=v1.1.0 python3 scripts/run_inquiry.py inquiry_001.pdf

# Compare results in database
```

### Query Version Used for a Report
```sql
SELECT agent_type, prompt_version
FROM agent_outputs
WHERE session_id = 'abc-123';
```

### Rollback to Previous Version
```bash
# Just change config
# backend/app/config.py
extractor_prompt_version = "v1.0.0"  # Rollback from v1.1.0

# Or use environment variable
EXTRACTOR_PROMPT_VERSION=v1.0.0 uvicorn app.main:app --reload
```

---

## Version Naming

**Format:** `vMAJOR.MINOR.PATCH`

- **MAJOR (v2.0.0):** Breaking changes
  - Output format changed
  - Required field added/removed
  - Major behavioral shift

- **MINOR (v1.1.0):** New features
  - New instruction added
  - Significant prompt improvement
  - New section in output

- **PATCH (v1.0.1):** Bug fixes
  - Typo correction
  - Clarification of existing instruction
  - Minor wording adjustment

**Examples:**
- `v1.0.0 → v1.0.1`: Fixed typo in carcinogen detection instructions
- `v1.0.0 → v1.1.0`: Added customer question detection feature
- `v1.0.0 → v2.0.0`: Changed output from JSON to structured text

---

## File Locations

| Component | Path |
|-----------|------|
| **Versioned prompts** | `backend/app/agents/prompts/versions/` |
| **Version loader** | `backend/app/agents/prompts/versions/__init__.py` |
| **Configuration** | `backend/app/config.py` |
| **Database model** | `backend/app/models/database.py` (AgentOutput.prompt_version) |
| **Migration script** | `backend/scripts/migrations/add_prompt_version_column.py` |
| **Changelog** | `docs/development/PROMPT_CHANGELOG.md` |

---

## Agent Status

| Agent | Status | Version File |
|-------|--------|--------------|
| **EXTRACTOR** | ✅ Refactored | `extractor_v1_0_0.py` |
| **PLANNER** | ⏳ Pending | `planner_v1_0_0.py` (created, not integrated) |
| **WRITER** | ⏳ Pending | `writer_v1_0_0.py` (created, not integrated) |
| **RISK_ASSESSOR** | ⏳ Pending | `risk_assessor_v1_0_0.py` (created, not integrated) |
| **SUBAGENT** | ⏳ Pending | `subagent_v1_0_0.py` (created, not integrated) |

---

## Common Workflows

### 1. Engineer Reports Issue with Report Section

**Scenario:** "Positive Faktoren lists too many basic requirements"

**Steps:**
1. Identify responsible agent: WRITER (generates final report)
2. Check current version:
   ```sql
   SELECT prompt_version FROM agent_outputs
   WHERE session_id = '<session_id>' AND agent_type = 'writer';
   ```
3. Review current prompt:
   ```bash
   cat backend/app/agents/prompts/versions/writer_v1_0_0.py
   ```
4. Create improved version:
   ```bash
   cp writer_v1_0_0.py writer_v1_1_0.py
   # Edit: Add stricter filtering instructions
   ```
5. Test A/B:
   - Upload same inquiry with v1.0.0
   - Upload same inquiry with v1.1.0
   - Compare "Positive Faktoren" sections
6. Deploy if better:
   ```python
   # config.py
   writer_prompt_version = "v1.1.0"
   ```

### 2. Create New Prompt Version Based on Feedback

**Scenario:** Engineer feedback: "EXTRACTOR misses CAS numbers from German SDS tables"

**Implementation:**
```bash
# 1. Create new version
cd backend/app/agents/prompts/versions
cp extractor_v1_0_0.py extractor_v1_1_0.py

# 2. Edit extractor_v1_1_0.py
```

```python
VERSION = "v1.1.0"

CHANGELOG = """
v1.1.0 (2025-10-24) - Improve CAS number extraction from German SDS
- Added regex pattern for "CAS-Nr.:" format
- Added fallback parsing for "CAS: " vs "CAS-Nr: "
- Enhanced table column detection for German SDS Section 3
"""

PROMPT_TEMPLATE = """
... existing prompt ...

**ENHANCED CAS NUMBER EXTRACTION (German SDS):**
When extracting from German Safety Data Sheets (Sicherheitsdatenblatt), check for these variations:
- "CAS-Nr.: 50-00-0"
- "CAS: 50-00-0"
- "CAS-Nummer: 50-00-0"
- Table column headers: "CAS-Nr.", "CAS-Nummer", "CAS Number"

... rest of prompt ...
"""
```

```bash
# 3. Update config
# backend/app/config.py
# extractor_prompt_version = "v1.1.0"

# 4. Test on problematic SDS
pytest tests/integration/test_extractor.py -k test_german_sds

# 5. Document in changelog
echo "## EXTRACTOR\n\n### v1.1.0 (2025-10-24)\n**Changes:** Improved CAS extraction from German SDS" >> docs/development/PROMPT_CHANGELOG.md

# 6. Commit
git add .
git commit -m "[PROMPT][EXTRACTOR] v1.1.0: Improve German SDS CAS extraction"
git tag prompt-extractor-v1.1.0
```

### 3. Rollback Bad Prompt Version

**Scenario:** WRITER v1.2.0 generates reports that are too verbose

**Rollback:**
```bash
# Option 1: Config rollback (instant)
# backend/app/config.py
writer_prompt_version = "v1.1.0"  # Was v1.2.0
# Restart server: uvicorn app.main:app --reload

# Option 2: Environment variable (no restart needed)
WRITER_PROMPT_VERSION=v1.1.0 uvicorn app.main:app --reload

# Option 3: Git revert (if version file has issues)
git revert <commit-hash-of-v1.2.0>
```

---

## Semantic Versioning Examples

### PATCH (v1.0.0 → v1.0.1)
```diff
- **CRITICAL**: Pay special attention to tables.rows
+ **CRITICAL**: Pay special attention to tables.rows - this contains critical data
```
**Rationale:** Clarification, no behavioral change

### MINOR (v1.0.0 → v1.1.0)
```diff
+ **CUSTOMER QUESTION DETECTION:**
+ Scan documents for explicit questions and capture in customer_specific_questions array.
```
**Rationale:** New feature, backward compatible

### MAJOR (v1.0.0 → v2.0.0)
```diff
- Return JSON with pollutant_list array
+ Return structured text with VOC Analysis section followed by Process Parameters section
```
**Rationale:** Breaking change in output format

---

## Environment Variables

Override prompt versions without editing config.py:

```bash
# backend/.env
EXTRACTOR_PROMPT_VERSION=v1.1.0
PLANNER_PROMPT_VERSION=v1.0.0
WRITER_PROMPT_VERSION=v1.2.0
RISK_ASSESSOR_PROMPT_VERSION=v1.0.1
SUBAGENT_PROMPT_VERSION=v1.0.0
```

**Use case:** Test specific version combination without code changes

---

## Debugging

### Check Which Version Was Used
```python
from app.agents.prompts.versions import get_prompt_version
from app.config import settings

data = get_prompt_version("extractor", settings.extractor_prompt_version)
print(f"Using EXTRACTOR version: {data['VERSION']}")
print(f"Prompt length: {len(data['PROMPT_TEMPLATE'])} chars")
```

### List All Available Versions
```python
from app.agents.prompts.versions import list_available_versions

for agent in ["extractor", "planner", "writer", "risk_assessor", "subagent"]:
    versions = list_available_versions(agent)
    print(f"{agent}: {versions}")
```

### View Version Changelog
```bash
# View specific version
cat backend/app/agents/prompts/versions/extractor_v1_1_0.py | grep -A 10 "CHANGELOG"

# View all changelogs
cat docs/development/PROMPT_CHANGELOG.md
```

---

## Best Practices

1. **Always test before deploying:**
   - Run integration tests with new version
   - A/B compare with previous version on 2-3 inquiries

2. **Document rationale:**
   - Update `CHANGELOG` in version file
   - Update `docs/development/PROMPT_CHANGELOG.md`
   - Reference engineer feedback or issue number

3. **Use semantic versioning correctly:**
   - PATCH for clarifications
   - MINOR for new features
   - MAJOR for breaking changes

4. **Commit atomic changes:**
   ```bash
   git add app/agents/prompts/versions/extractor_v1_1_0.py
   git add app/config.py
   git add docs/development/PROMPT_CHANGELOG.md
   git commit -m "[PROMPT][EXTRACTOR] v1.1.0: Specific change description"
   git tag prompt-extractor-v1.1.0
   ```

5. **Keep old versions:**
   - Never delete old version files
   - They enable rollback and historical analysis

---

## Troubleshooting

### "ImportError: No module named extractor_v1_1_0"
**Cause:** Version file doesn't exist
**Fix:**
```bash
ls backend/app/agents/prompts/versions/extractor_*.py  # Check what versions exist
# Create missing version or update config to use existing version
```

### "KeyError: PROMPT_TEMPLATE"
**Cause:** Version file missing required field
**Fix:** Ensure version file has:
```python
VERSION = "v1.0.0"
CHANGELOG = """..."""
SYSTEM_PROMPT = """..."""
PROMPT_TEMPLATE = """..."""
```

### "Prompt uses old version despite config change"
**Cause:** Server not restarted or .env not loaded
**Fix:**
```bash
# Restart uvicorn
# Or check .env is being loaded
python3 -c "from app.config import settings; print(settings.extractor_prompt_version)"
```

---

## Migration Checklist

When adding prompt versioning to a new agent:

- [ ] Extract prompt to `{agent}_v1_0_0.py`
- [ ] Add `{agent}_prompt_version` to `config.py`
- [ ] Refactor agent node to use `get_prompt_version()`
- [ ] Update agent node to log `prompt_version` to database
- [ ] Add integration test for versioning
- [ ] Document in `PROMPT_CHANGELOG.md`
- [ ] Test full workflow end-to-end

---

## Support

**Questions?**
- Check `PROMPT_VERSIONING_IMPLEMENTATION_SUMMARY.md` for detailed explanation
- Review `PROMPT_CHANGELOG.md` for version history
- Search codebase: `git grep "get_prompt_version"`

**Issues?**
- Check git logs: `git log --grep="PROMPT" --oneline`
- Query database: `SELECT DISTINCT prompt_version FROM agent_outputs;`
- Rollback: Change config to previous version
