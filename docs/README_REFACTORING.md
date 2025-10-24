# Agent Refactoring Documentation Index

**Last Updated:** 2025-10-23
**Status:** Phase 1 Complete ✅ | Ready for Implementation

---

## 📚 Quick Navigation

### Start Here

| If you want to... | Read this document |
|-------------------|-------------------|
| **Understand what was implemented** | [`REFACTORING_PROJECT_SUMMARY.md`](development/REFACTORING_PROJECT_SUMMARY.md) ⭐ |
| **See the architecture visually** | [`AGENT_REFACTORING_ARCHITECTURE.md`](architecture/AGENT_REFACTORING_ARCHITECTURE.md) 📊 |
| **Implement the refactoring** | [`REFACTORING_STEP_BY_STEP_GUIDE.md`](development/REFACTORING_STEP_BY_STEP_GUIDE.md) 🔧 |
| **Understand the requirements** | [`agent_refactoring_instructions.md`](architecture/agent_refactoring_instructions.md) 📋 |
| **Learn how versioning works** | [`PROMPT_VERSIONING_QUICK_REFERENCE.md`](development/PROMPT_VERSIONING_QUICK_REFERENCE.md) ⚡ |

---

## 📖 Document Descriptions

### Overview Documents

#### 1. **REFACTORING_PROJECT_SUMMARY.md** ⭐ START HERE
**Location:** `docs/development/`
**Purpose:** Executive summary of the entire refactoring project
**Contains:**
- What has been delivered (Phase 1 complete)
- What needs to be implemented (Phases 2-4)
- Quick start instructions
- Success metrics
- Next steps

**Read this first** to understand the project scope and current status.

---

#### 2. **agent_refactoring_instructions.md** 📋 ORIGINAL REQUIREMENTS
**Location:** `docs/architecture/`
**Purpose:** Original refactoring requirements (your reference document)
**Contains:**
- Detailed change specifications for each agent
- Line-by-line edit instructions
- JSON schema updates
- Validation checklists
- Migration notes

**This is the authoritative source** for what needs to be changed.

---

### Visual Architecture

#### 3. **AGENT_REFACTORING_ARCHITECTURE.md** 📊 VISUAL GUIDE
**Location:** `docs/architecture/`
**Purpose:** Visual diagrams showing before/after architecture
**Contains:**
- ASCII diagrams of current problems
- ASCII diagrams of new architecture
- Data flow transformations
- Architectural principles
- Schema changes with examples

**Read this** to understand the "why" behind the refactoring.

---

### Implementation Guide

#### 4. **REFACTORING_STEP_BY_STEP_GUIDE.md** 🔧 IMPLEMENTATION
**Location:** `docs/development/`
**Purpose:** Detailed step-by-step implementation instructions
**Contains:**
- Phase 2: EXTRACTOR refactoring (Week 1)
- Phase 3: PLANNER refactoring (Week 2)
- Phase 4: Downstream agents (Week 3)
- Code examples for every change
- Testing commands
- Rollback procedures

**Use this** as your implementation checklist.

---

### Usage Documentation

#### 5. **REFACTORING_IMPLEMENTATION_SUMMARY.md** ✅ USAGE GUIDE
**Location:** `docs/development/`
**Purpose:** Comprehensive overview with usage instructions
**Contains:**
- How to use the versioning system
- Creating new prompt versions
- Integrating versioning into agent nodes
- A/B testing procedures
- Rollback strategies

**Read this** to learn how to work with the versioning system.

---

#### 6. **PROMPT_VERSIONING_QUICK_REFERENCE.md** ⚡ QUICK COMMANDS
**Location:** `docs/development/`
**Purpose:** Quick reference for common tasks
**Contains:**
- Quick commands for version management
- Common workflows (create version, A/B test, rollback)
- Troubleshooting guide
- Best practices

**Bookmark this** for day-to-day development.

---

### Tracking Documents

#### 7. **PROMPT_CHANGELOG.md** 📝 VERSION HISTORY
**Location:** `docs/development/`
**Purpose:** Track all prompt version changes
**Contains:**
- Version history for each agent
- Change descriptions
- Dates and authors
- Rollback records

**Update this** every time you create a new prompt version.

---

## 🎯 Reading Order by Role

### For Project Managers

1. **REFACTORING_PROJECT_SUMMARY.md** - Understand scope and timeline
2. **AGENT_REFACTORING_ARCHITECTURE.md** - See the "why"
3. **REFACTORING_STEP_BY_STEP_GUIDE.md** - Understand implementation phases

### For Developers

1. **REFACTORING_PROJECT_SUMMARY.md** - Get overview
2. **PROMPT_VERSIONING_QUICK_REFERENCE.md** - Learn the system
3. **REFACTORING_STEP_BY_STEP_GUIDE.md** - Follow implementation steps
4. **agent_refactoring_instructions.md** - Reference for detailed specs

### For QA/Testing

1. **REFACTORING_PROJECT_SUMMARY.md** - Understand changes
2. **REFACTORING_STEP_BY_STEP_GUIDE.md** - See testing strategies
3. **PROMPT_VERSIONING_QUICK_REFERENCE.md** - Learn A/B testing commands

---

## 🗂️ File Structure

```
Repository_Evaluator/
├── docs/
│   ├── README_REFACTORING.md                    # ← YOU ARE HERE
│   │
│   ├── architecture/
│   │   ├── agent_refactoring_instructions.md    # Original requirements
│   │   └── AGENT_REFACTORING_ARCHITECTURE.md    # Visual architecture
│   │
│   └── development/
│       ├── REFACTORING_PROJECT_SUMMARY.md       # ⭐ Start here
│       ├── REFACTORING_IMPLEMENTATION_SUMMARY.md # Usage guide
│       ├── REFACTORING_STEP_BY_STEP_GUIDE.md    # Implementation steps
│       ├── PROMPT_VERSIONING_QUICK_REFERENCE.md # Quick commands
│       └── PROMPT_CHANGELOG.md                  # Version history
│
└── backend/
    └── app/
        └── agents/
            └── prompts/
                ├── __init__.py                  # Shared fragments
                └── versions/
                    ├── __init__.py              # Version loader
                    ├── extractor_v1_0_0.py      # EXTRACTOR baseline
                    ├── planner_v1_0_0.py        # PLANNER baseline
                    ├── subagent_v1_0_0.py       # SUBAGENT baseline
                    ├── risk_assessor_v1_0_0.py  # RISK_ASSESSOR baseline
                    └── writer_v1_0_0.py         # WRITER baseline
```

---

## 🚀 Quick Start

### 1. Understand the Project (30 minutes)

```bash
# Read the executive summary
cat docs/development/REFACTORING_PROJECT_SUMMARY.md

# View the architecture diagrams
cat docs/architecture/AGENT_REFACTORING_ARCHITECTURE.md
```

### 2. Verify Infrastructure (5 minutes)

```bash
cd backend
source .venv/bin/activate

# Test prompt versioning system
python3 -c "from app.agents.prompts.versions import get_prompt_version; \
print('✅ Version:', get_prompt_version('extractor', 'v1.0.0')['VERSION'])"

# List available versions
python3 -c "from app.agents.prompts.versions import list_available_versions; \
for agent in ['extractor', 'planner', 'writer', 'risk_assessor', 'subagent']: \
    print(f'{agent}: {list_available_versions(agent)}')"
```

### 3. Start Implementation (Follow Guide)

```bash
# Open step-by-step guide
cat docs/development/REFACTORING_STEP_BY_STEP_GUIDE.md

# Start with EXTRACTOR refactoring (Week 1)
cd app/agents/prompts/versions
cp extractor_v1_0_0.py extractor_v2_0_0.py

# Follow Phase 2 instructions in the guide
```

---

## 📋 Implementation Checklist

### Phase 1: Infrastructure ✅ COMPLETE

- [x] Prompt versioning system implemented
- [x] Shared fragments library created
- [x] Database schema updated
- [x] Documentation written
- [x] Version loader API tested

### Phase 2: EXTRACTOR (Week 1) ⏳ READY

- [ ] Create `extractor_v2_0_0.py`
- [ ] Remove carcinogen detection
- [ ] Add extraction_notes system
- [ ] Add technical cleanup rules
- [ ] Update JSON schema
- [ ] Test with unit tests
- [ ] A/B compare with v1.0.0
- [ ] Update config to v2.0.0
- [ ] Update PROMPT_CHANGELOG.md
- [ ] Commit and tag

### Phase 3: PLANNER (Week 2) ⏳ READY

- [ ] Create `planner_v2_0_0.py`
- [ ] Add Phase 1: Data Enrichment
- [ ] Add Phase 2: Conditional subagent creation
- [ ] Implement web_search for CAS lookup
- [ ] Update planner node code
- [ ] Test enrichment phase
- [ ] Test subagent creation logic
- [ ] Update config to v2.0.0
- [ ] Update PROMPT_CHANGELOG.md
- [ ] Commit and tag

### Phase 4: Downstream Agents (Week 3) ⏳ READY

- [ ] SUBAGENT v1.1.0 (uncertainty quantification)
- [ ] RISK_ASSESSOR v2.0.0 (synthesizer role)
- [ ] WRITER v1.1.0 (Risk Assessor priority)
- [ ] Test full pipeline
- [ ] Generate 5 feasibility reports
- [ ] Engineer validation

### Phase 5: Production Rollout (Week 4-5) ⏳ PLANNED

- [ ] Deploy to staging
- [ ] Monitor metrics (error rate, token usage, duration)
- [ ] Week 4: 20% traffic to new system
- [ ] Week 5: 100% migration
- [ ] Collect engineer feedback

---

## 🔍 Finding Information

### Common Questions

**Q: What's the current status of the project?**
A: See `REFACTORING_PROJECT_SUMMARY.md` → "Executive Summary"

**Q: How do I create a new prompt version?**
A: See `PROMPT_VERSIONING_QUICK_REFERENCE.md` → "Create New Version"

**Q: What exactly needs to change in EXTRACTOR?**
A: See `agent_refactoring_instructions.md` → Section 1 (lines 24-184)

**Q: How do I test my changes?**
A: See `REFACTORING_STEP_BY_STEP_GUIDE.md` → "Step 2: Test"

**Q: What if something goes wrong?**
A: See `REFACTORING_STEP_BY_STEP_GUIDE.md` → "Rollback Procedure"

**Q: Why are we doing this refactoring?**
A: See `AGENT_REFACTORING_ARCHITECTURE.md` → "Current Problem"

---

## 📊 Monitoring and Validation

### Check Current Versions

```sql
-- Which versions are currently deployed?
SELECT agent_type, prompt_version, COUNT(*)
FROM agent_outputs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, prompt_version;
```

### Monitor Performance

```sql
-- Error rate by version
SELECT
  agent_type,
  prompt_version,
  COUNT(*) FILTER (WHERE status = 'failed') * 100.0 / COUNT(*) as error_rate_pct
FROM agent_outputs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, prompt_version;

-- Average duration and token usage
SELECT
  agent_type,
  prompt_version,
  AVG(duration_seconds) as avg_duration_sec,
  AVG(token_usage) as avg_tokens
FROM agent_outputs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type, prompt_version;
```

---

## 🆘 Troubleshooting

### Issue: "ImportError: No module named extractor_v2_0_0"

**Solution:**
```bash
# Check if version file exists
ls backend/app/agents/prompts/versions/extractor_*.py

# If missing, create it
cp extractor_v1_0_0.py extractor_v2_0_0.py
```

**Reference:** `PROMPT_VERSIONING_QUICK_REFERENCE.md` → "Troubleshooting"

---

### Issue: "Config updated but agent still uses old version"

**Solution:**
```bash
# Restart server to reload config
uvicorn app.main:app --reload

# Or use environment variable override
EXTRACTOR_PROMPT_VERSION=v2.0.0 uvicorn app.main:app --reload
```

**Reference:** `PROMPT_VERSIONING_QUICK_REFERENCE.md` → "Troubleshooting"

---

### Issue: "Need to rollback to previous version"

**Solution:**
```bash
# Edit config
# backend/app/config.py: extractor_prompt_version = "v1.0.0"

# Restart server
uvicorn app.main:app --reload

# Document rollback in CHANGELOG
```

**Reference:** `REFACTORING_STEP_BY_STEP_GUIDE.md` → "Rollback Procedure"

---

## 📞 Support

### For Questions About...

**Requirements and specifications:**
- Read: `agent_refactoring_instructions.md`
- Search: Grep for specific agent name or feature

**Implementation details:**
- Read: `REFACTORING_STEP_BY_STEP_GUIDE.md`
- Follow: Step-by-step instructions for your phase

**Architecture and design:**
- Read: `AGENT_REFACTORING_ARCHITECTURE.md`
- See: Visual diagrams and data flow

**Day-to-day usage:**
- Read: `PROMPT_VERSIONING_QUICK_REFERENCE.md`
- Bookmark: Quick commands section

**Project status:**
- Read: `REFACTORING_PROJECT_SUMMARY.md`
- Check: Implementation checklist

---

## 🎓 Learning Path

### Day 1: Orientation

1. Read `REFACTORING_PROJECT_SUMMARY.md` (30 min)
2. Read `AGENT_REFACTORING_ARCHITECTURE.md` (20 min)
3. Verify infrastructure with quick start commands (10 min)

### Day 2: Deep Dive

1. Read `REFACTORING_STEP_BY_STEP_GUIDE.md` Phase 2 (30 min)
2. Read `agent_refactoring_instructions.md` EXTRACTOR section (20 min)
3. Review existing prompt: `extractor_v1_0_0.py` (20 min)

### Day 3: Implementation Prep

1. Set up test environment (30 min)
2. Identify 10 historical inquiries for A/B testing (30 min)
3. Create implementation branch: `git checkout -b refactor-extractor-v2`

### Week 1: EXTRACTOR Implementation

Follow `REFACTORING_STEP_BY_STEP_GUIDE.md` → Phase 2

### Week 2: PLANNER Implementation

Follow `REFACTORING_STEP_BY_STEP_GUIDE.md` → Phase 3

### Week 3: Downstream Agents

Follow `REFACTORING_STEP_BY_STEP_GUIDE.md` → Phase 4

---

## ✅ Success Criteria

### Phase 1 (Infrastructure) ✅

- [x] Versioning system works
- [x] Shared fragments available
- [x] Database tracks versions
- [x] Documentation complete

### Phase 2 (EXTRACTOR) ⏳

- [ ] Prompt size reduced 50%
- [ ] extraction_notes populated
- [ ] No business logic remains
- [ ] Tests pass
- [ ] A/B validation shows improvement

### Phase 3 (PLANNER) ⏳

- [ ] CAS lookup works
- [ ] Conditional subagent creation tested
- [ ] Enrichment phase validated
- [ ] Tests pass

### Phase 4 (Full Pipeline) ⏳

- [ ] All agents refactored
- [ ] End-to-end test passes
- [ ] Feasibility reports improved (engineer validation)
- [ ] Performance maintained (±10%)

---

## 📈 Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| **Week 0** | Infrastructure | ✅ Versioning system |
| **Week 1** | EXTRACTOR | `extractor_v2_0_0.py` |
| **Week 2** | PLANNER | `planner_v2_0_0.py` |
| **Week 3** | Downstream | `subagent_v1_1_0.py`, `risk_assessor_v2_0_0.py`, `writer_v1_1_0.py` |
| **Week 4** | Staging | 20% traffic rollout |
| **Week 5** | Production | 100% migration |

---

## 🏁 Conclusion

This index provides a complete map of the refactoring documentation. Start with `REFACTORING_PROJECT_SUMMARY.md` for an overview, then follow the step-by-step guide for implementation.

**Phase 1 is complete. You're ready to begin Phase 2 (EXTRACTOR refactoring).**

Good luck! 🚀

---

**Last Updated:** 2025-10-23
**Maintainer:** Andreas
**Project:** Oxytec Multi-Agent Feasibility Platform - Agent Refactoring
