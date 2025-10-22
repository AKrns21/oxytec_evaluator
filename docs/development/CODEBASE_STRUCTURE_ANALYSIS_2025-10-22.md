# Oxytec Multi-Agent Feasibility Platform - Codebase Structure & Cleanup Analysis

## Executive Summary

This is a well-structured FastAPI/React application with a dynamic multi-agent system powered by LangGraph. The codebase is **generally clean** with some opportunities for consolidation. The main issues are orphaned/empty directories and documentation fragmentation.

---

## Part 1: Complete Directory Structure

### Backend Structure (`/backend`)

```
backend/
├── app/
│   ├── agents/              # LangGraph multi-agent workflow
│   │   ├── nodes/           # Individual agent nodes (5 agents)
│   │   │   ├── extractor.py         (668 lines) - Extracts facts from documents
│   │   │   ├── planner.py            (291 lines) - Plans subagent strategies
│   │   │   ├── subagent.py           (690 lines) - Executes parallel subagents
│   │   │   ├── risk_assessor.py      (393 lines) - Risk analysis & synthesis
│   │   │   └── writer.py             (465 lines) - Final report generation
│   │   ├── {nodes}/         [EMPTY - ORPHANED] Delete
│   │   ├── state.py         (39 lines) - GraphState TypedDict definition
│   │   ├── graph.py         (168 lines) - LangGraph workflow orchestration
│   │   ├── tools.py         (308 lines) - Tool definitions & execution
│   │   ├── prompts.py       (266 lines) - Shared prompt templates
│   │   ├── timing.py        - Agent execution timing
│   │   ├── validation.py    - Output validation
│   │   └── __init__.py
│   │
│   ├── api/                 # FastAPI endpoints
│   │   ├── routes/
│   │   │   ├── upload.py    - File upload & session creation
│   │   │   ├── session.py   - Session status & results
│   │   │   ├── stream.py    - Server-Sent Events for real-time updates
│   │   │   └── __init__.py
│   │   ├── {routes}/        [EMPTY - ORPHANED] Delete
│   │   ├── dependencies.py  - API dependencies
│   │   └── __init__.py
│   │
│   ├── services/            # Business logic layer (1,770 lines total)
│   │   ├── llm_service.py            (355 lines) - LLM API wrapper (Anthropic & OpenAI)
│   │   ├── document_service.py       (677 lines) - Multi-format document extraction
│   │   ├── embedding_service.py      (80 lines)  - OpenAI embeddings
│   │   ├── rag_service.py            (144 lines) - Product database semantic search
│   │   ├── technology_rag_service.py (317 lines) - Technology KB semantic search
│   │   ├── pdf_service.py            (197 lines) - PDF generation from markdown
│   │   └── __init__.py
│   │
│   ├── models/
│   │   ├── database.py      - SQLAlchemy ORM models (sessions, documents, products, embeddings)
│   │   ├── schemas.py       - Pydantic request/response schemas
│   │   └── __init__.py
│   │
│   ├── utils/               # Utility functions (specialized validators)
│   │   ├── logger.py                     - Structured logging (structlog)
│   │   ├── helpers.py                    - Generic helpers (hashing, file ops)
│   │   ├── extraction_quality_validator.py - LLM output validation
│   │   ├── cas_validator.py              - CAS number validation utility
│   │   ├── substance_corrections.py      - Post-processing corrections
│   │   └── __init__.py
│   │
│   ├── db/
│   │   ├── session.py       - Async database session & connection pooling
│   │   ├── {migrations}/    [EMPTY - ORPHANED] Delete
│   │   └── __init__.py
│   │
│   ├── config.py            - Pydantic Settings configuration (all env vars)
│   ├── main.py              - FastAPI app initialization
│   └── __init__.py
│
├── tests/
│   ├── unit/                - Unit tests [MINIMAL - NEEDS EXPANSION]
│   ├── integration/         - Integration tests [EMPTY]
│   ├── e2e/                 - End-to-end tests [EMPTY]
│   ├── evaluation/
│   │   └── extractor/       - Extractor quality evaluation framework
│   │       ├── layer1_document_parsing/    - PDF/XLSX parsing tests
│   │       ├── layer2_llm_interpretation/  - LLM extraction quality tests
│   │       └── utils/                      - Comparison & validation utilities
│   └── README.md
│
├── migrations/
│   └── 001_add_vector_indexes.sql  - Database schema migrations
│
├── docs/
│   ├── setup/               - Setup guides (LangSmith, Supabase, RAG)
│   ├── implementation/      - Implementation summaries & feature docs
│   ├── api/                 - API documentation [EMPTY]
│   ├── reports/             - Generated feasibility report PDFs
│   └── README.md
│
├── uploads/                 - User uploaded files (session directories)
├── backend.log              - Runtime logs
├── pyproject.toml           - Project dependencies & tool config
└── Dockerfile
```

### Frontend Structure (`/frontend`)

```
frontend/
├── app/
│   ├── page.tsx                       - Main upload page
│   ├── layout.tsx                     - Root layout with fonts/metadata
│   ├── globals.css                    - Global styles
│   ├── session/[id]/page.tsx          - Session results viewer page
│   └── upload/                        [UNUSED - old routing pattern]
│
├── components/
│   ├── FileUpload.tsx                 - Drag-and-drop file upload component
│   ├── ResultsViewer.tsx              - Report display component
│   ├── AgentVisualization.tsx         - Agent execution flow visualization
│   ├── {ui}/                          [EMPTY - ORPHANED] Delete
│   └── ui/                            - shadcn/ui components
│       ├── button.tsx, card.tsx, input.tsx, label.tsx, progress.tsx, tabs.tsx
│
├── hooks/
│   └── useSSE.ts                      - Server-Sent Events hook for real-time updates
│
├── lib/
│   └── utils.ts                       - Utility functions (cn for classname merging)
│
├── types/
│   └── session.ts                     - TypeScript interfaces (SessionStatus, AgentUpdate)
│
├── public/                            - Static assets
├── next.config.js                     - Next.js configuration
├── tailwind.config.ts                 - TailwindCSS configuration
├── tsconfig.json                      - TypeScript configuration
├── package.json                       - Dependencies
├── package-lock.json
├── postcss.config.js
└── Dockerfile
```

### Project Root Level

```
/
├── CLAUDE.md                          - AI assistant instructions (comprehensive)
├── README.md                          - Project overview
├── QUICKSTART.md                      - Quick start guide
├── BACKEND_RUNNING.md                 - Backend setup notes
├── FRONTEND_SETUP.md                  - Frontend setup notes
├── PROJECT_STATUS.md                  - Project status tracking
├── oxytec-platform-architecture.md    - Architecture documentation
│
├── docker-compose.yml                 - Docker Compose for full stack
├── .gitignore                         - Git ignore patterns
├── .DS_Store                          - macOS file (should be in .gitignore)
│
├── docs/
│   ├── architecture/                  - System design & architecture docs
│   ├── development/                   - Code reviews & prompt engineering updates
│   ├── evaluation/                    - Testing strategies & evaluation frameworks
│   ├── examples/                      - Example outputs & sample data
│   └── README.md
│
├── backend/                           - [Detailed above]
└── frontend/                          - [Detailed above]
```

### Additional Directories Found

```
.claude/                               - [Claude.ai IDE cache/metadata]
├── agents/                            - IDE agent configurations
└── settings.local.json                - IDE local settings

frontend/.next/                        - [Next.js build cache - ignore]
frontend/node_modules/                 - [Dependencies - ignore]
```

---

## Part 2: Codebase Statistics

### Backend Code Metrics

| Category | Count | Notes |
|----------|-------|-------|
| Python source files | 56 | Core backend modules |
| Test files (test_*.py) | 7 | Minimal test coverage |
| Agent node files | 5 | Core workflow agents |
| Service modules | 7 | Business logic layer |
| Utility modules | 5 | Helper functions |
| API route modules | 3 | REST endpoints |
| Total backend lines of code | ~2,500 | Excluding docs & tests |

### Frontend Code Metrics

| Category | Count | Notes |
|----------|-------|-------|
| React components | 3 | Core UI components |
| shadcn/ui components | 6 | Pre-built UI elements |
| Custom hooks | 1 | Server-Sent Events |
| TypeScript files | 16 | Including app pages & configs |
| Total frontend lines of code | ~1,500 | Excluding node_modules |

### Documentation

| Category | Count | Notes |
|----------|-------|-------|
| Root documentation files | 10 | High-level guides |
| Project docs | 15 | Architecture, development, evaluation |
| Backend docs | 19 | Implementation, setup, API docs |
| Total markdown files | ~845 | Includes node_modules docs |

---

## Part 3: Identified Issues & Cleanup Opportunities

### Critical Issues (High Priority)

#### 1. Orphaned Empty Directories [DELETE]

These are placeholder directories that are no longer used:

```
backend/app/agents/{nodes}/           - EMPTY - DELETE
backend/app/api/{routes}/             - EMPTY - DELETE
backend/app/db/{migrations}/          - EMPTY - DELETE
frontend/components/{ui}/             - EMPTY - DELETE
```

**Action**: Remove these 4 empty directories completely.

---

#### 2. Potentially Unused Utility Files

**File**: `backend/app/utils/cas_validator.py`
- **Status**: ORPHANED
- **Usage**: Only imported by `extraction_quality_validator.py` but that function is not called elsewhere
- **Lines**: 197 lines
- **Action**: Check if `extraction_quality_validator.py` is actually used. If not used, both can be removed.

**File**: `backend/app/utils/extraction_quality_validator.py`
- **Status**: NOT INTEGRATED
- **Lines**: 297 lines
- **Usage**: Imported in `extractor.py` but the `validate_extracted_facts()` function is never called
- **Action**: Either integrate into extractor or remove if not needed.

**File**: `backend/app/utils/substance_corrections.py`
- **Status**: SEMI-USED
- **Lines**: 155 lines
- **Usage**: Used in `extractor.py` for post-processing corrections
- **Action**: Keep (actively used)

---

#### 3. Unused Frontend Routes

**Path**: `frontend/app/upload/`
- **Status**: ORPHANED
- **Issue**: Old routing pattern - upload now happens on main page
- **Action**: Delete this directory (migration to main page.tsx already complete)

---

### Medium Priority Issues

#### 4. Complex & Large Modules Needing Simplification

| Module | Lines | Complexity | Issue |
|--------|-------|-----------|-------|
| `subagent.py` | 690 | High | Very large; mixing concerns (coordination, execution, prompt building) |
| `extractor.py` | 668 | High | Large; multiple responsibilities (extraction, validation, cleaning) |
| `document_service.py` | 677 | High | Multi-format handling creates branching complexity |
| `writer.py` | 465 | Medium | Report generation with embedded formatting logic |

**Recommendation**: Consider extracting concerns:
- `subagent.py`: Split into `subagent_executor.py`, `subagent_definitions.py`, `subagent_prompt_builder.py`
- `extractor.py`: Extract `data_cleaning.py` for `normalize_units()` and `clean_extracted_data()`
- `document_service.py`: Extract format handlers into separate modules

#### 5. Documentation Fragmentation

**Issue**: Documentation is scattered across multiple locations:
- Root level docs (CLAUDE.md, README.md, etc.)
- `docs/` directory (architecture, development, evaluation)
- `backend/docs/` directory (setup, implementation, api)
- Implementation notes embedded in code

**Current State**:
- Many overlapping setup guides
- Scattered implementation notes
- No single source of truth for architecture

**Recommendation**: Consolidate:
1. Move all project-level architecture → `docs/architecture/`
2. Move all setup guides → `backend/docs/setup/`
3. Create unified API documentation → `backend/docs/api/`
4. Archive old implementation docs (keep latest version only)

---

#### 6. Limited Test Coverage

**Current State**:
- 7 test files (all in evaluation/extractor)
- 0 tests for: agents, services, API endpoints, utilities
- No unit tests for critical business logic
- No integration tests for graph workflow

**Missing Tests**:
- Unit tests for `rag_service.py`, `llm_service.py`, `embedding_service.py`
- Integration tests for complete agent graph
- API endpoint tests (upload, session, stream)
- Tool executor tests

**Recommendation**: Add baseline test coverage:
- `tests/unit/test_llm_service.py`
- `tests/unit/test_rag_services.py`
- `tests/integration/test_agent_graph.py`
- `tests/integration/test_api_endpoints.py`

---

### Low Priority Issues

#### 7. Code Pattern Inconsistencies

**Issue**: Some inconsistencies in error handling patterns:

```python
# Pattern 1: Detailed error logging with context
logger.error("operation_failed", 
    context_data=value,
    error=str(e),
    exception_type=type(e).__name__)

# Pattern 2: Simple string logging
logger.error("error occurred: " + str(e))

# Pattern 3: Silent failures with try/except
try:
    operation()
except Exception:
    pass
```

**Recommendation**: Standardize on Pattern 1 (structured logging) across all modules.

---

#### 8. Unused Dependencies (Possible)

**Files to check**:
- `tenacity` - only visible in pyproject.toml, search actual usage
- `reportlab` - only used by xhtml2pdf internally
- Some imports in files may be unused

**Recommendation**: Run `ruff` to identify unused imports:
```bash
cd backend
ruff check app/ --select=F401  # Find unused imports
```

---

#### 9. Configuration Over-Specification

**File**: `backend/app/config.py`
- **Issue**: Contains many settings that are rarely changed:
  - `excel_max_preview_rows: int = 50`
  - `excel_statistical_threshold: float = 0.5`
  - Multiple model-specific temperature settings

**Recommendation**: 
- Keep only runtime-critical settings in config
- Move development constants into code as module-level constants
- Or keep as-is if flexibility is intentional

---

#### 10. Missing Type Hints in Some Areas

**Files with partial typing**:
- `tools.py`: Uses `Any` and `Dict` frequently instead of specific types
- Some response handlers use loose types
- Frontend TypeScript has loose `any` types in places

**Recommendation**: Add stricter typing for better IDE support and type safety.

---

## Part 4: Code Quality Observations

### Strengths

1. **Modular Architecture**: Clear separation of concerns
   - API layer (routes)
   - Service layer (business logic)
   - Agent layer (workflow)
   - Models/schemas (data)

2. **Async-First Design**: Proper async/await usage throughout
   - Async database queries
   - Parallel subagent execution
   - Async FastAPI handlers

3. **Comprehensive Logging**: Structured logging with context
   - Consistent use of structlog
   - Good tracing capability
   - LangSmith integration ready

4. **Configuration Management**: Clean Pydantic settings
   - Environment-driven configuration
   - Type-safe settings
   - Good defaults

5. **Frontend/Backend Integration**: Clean API design
   - RESTful endpoints
   - Server-Sent Events for real-time updates
   - Proper error handling in UI

### Weaknesses

1. **Large Monolithic Files**: Some files are doing too much
   - `subagent.py` (690 lines) - should be split
   - `extractor.py` (668 lines) - should be split
   - `document_service.py` (677 lines) - consider format handlers

2. **Minimal Testing**: Evaluation-only tests
   - No unit test coverage for core business logic
   - No integration tests for workflows
   - No API endpoint tests

3. **Documentation Inconsistency**: 
   - Multiple documentation locations
   - Some overlap between docs
   - Some implementation notes only in code comments

4. **Unused/Dead Code**:
   - Empty orphaned directories
   - Potentially unused validator modules
   - Old frontend routes

5. **Error Handling**: Inconsistent patterns
   - Some functions silently fail
   - Some use structured logging, others use simple strings
   - Unrecoverable errors sometimes swallowed

---

## Part 5: Cleanup Roadmap

### Phase 1: Quick Wins (1-2 hours)

1. Delete orphaned directories:
   ```bash
   rm -rf backend/app/agents/{nodes}
   rm -rf backend/app/api/{routes}
   rm -rf backend/app/db/{migrations}
   rm -rf frontend/components/{ui}
   rm -rf frontend/app/upload
   ```

2. Check unused utilities:
   ```bash
   cd backend
   grep -r "cas_validator" --include="*.py"
   grep -r "extraction_quality_validator" --include="*.py"
   ```

3. Run import checker:
   ```bash
   cd backend
   ruff check app/ --select=F401
   ```

### Phase 2: Structural Improvements (4-6 hours)

1. Extract concerns from large files:
   - Split `subagent.py` into 3 smaller modules
   - Extract data cleaning functions from `extractor.py`
   - Consider format handlers for `document_service.py`

2. Add baseline tests:
   - Create unit test for `rag_service.py`
   - Create integration test for agent graph
   - Add API endpoint tests

3. Consolidate documentation:
   - Archive old implementation docs
   - Unify setup guides
   - Create single API reference

### Phase 3: Long-term (Ongoing)

1. Standardize error handling patterns
2. Add type hints to frontend
3. Expand test coverage to 70%+
4. Refactor large service methods

---

## Part 6: File Organization Best Practices

### Current Organization Compliance

The project **generally follows** CLAUDE.md guidelines:

✅ **Good**:
- Agent logic in `app/agents/`
- API routes thin (delegation to services)
- Services contain business logic
- Models/schemas properly separated
- Database operations in session/models

⚠️ **Partial**:
- Documentation could be more unified
- Some service methods are large

❌ **Needs Work**:
- Test coverage is minimal
- Some concerns not fully separated

---

## Part 7: Dead Code & Unused Code Patterns

### Definitely Dead

1. **Orphaned directories** (empty):
   - `backend/app/agents/{nodes}/`
   - `backend/app/api/{routes}/`
   - `backend/app/db/{migrations}/`
   - `frontend/components/{ui}/`

2. **Old routing**: `frontend/app/upload/` (superseded by main page)

### Likely Dead

1. **`extraction_quality_validator.py`**: 
   - Imported but function never called
   - Check if needed before committing

2. **`cas_validator.py`**:
   - Only used by extraction_quality_validator
   - Delete if extraction_quality_validator is unused

### Potentially Dead

1. **Commented-out code**: Search for patterns like:
   ```bash
   grep -r "^\s*#.*=" backend/app --include="*.py" | head -20
   ```

2. **Dev-only functions**: Some functions marked "for debugging"
   - Should be removed or moved to test utilities

---

## Part 8: Duplicate Code Patterns

### Code Duplication Found

1. **RAG Service Pattern**:
   - `rag_service.py` and `technology_rag_service.py` have similar structure
   - Both do: embed query → pgvector search → format results
   - **Recommendation**: Extract base class `BaseRAGService`

2. **Error Handling**:
   - Similar try/except/logger patterns across files
   - **Recommendation**: Create decorator `@handle_service_errors`

3. **State Initialization**:
   - Multiple places initialize empty GraphState fields
   - **Recommendation**: Create factory function `create_initial_state()`

### Service Similarity Analysis

```python
# Potential base class for RAG services
class BaseRAGService:
    async def search(self, query: str, top_k: int, **filters):
        embedding = await self.embedding_service.embed(query)
        results = await self._execute_search(embedding, **filters)
        return self._format_results(results)
    
    async def _execute_search(self, embedding, **filters):
        # Override in subclass
        pass
    
    def _format_results(self, results):
        # Override in subclass
        pass
```

---

## Summary of Recommendations

### Must Do (Cleanup)
- [x] Delete 4 orphaned empty directories
- [x] Delete old frontend upload route
- [ ] Verify and remove dead utility files

### Should Do (Quality)
- [ ] Add 15-20 unit tests for core services
- [ ] Split 3 large agent node files
- [ ] Consolidate documentation
- [ ] Extract duplicate patterns into shared code

### Nice to Have (Polish)
- [ ] Add type hints throughout frontend
- [ ] Standardize error handling
- [ ] Create base classes for RAG services
- [ ] Add comprehensive docstrings

---

## References

- **Architecture**: `CLAUDE.md` (project instructions)
- **Backend Docs**: `backend/docs/README.md`
- **Tests**: `backend/tests/README.md`
- **Documentation**: `docs/README.md`

