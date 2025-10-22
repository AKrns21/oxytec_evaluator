# Backend Documentation

This directory contains backend-specific documentation for the Oxytec platform.

## Directory Organization

### `/setup`
Setup and configuration guides:
- **LANGSMITH_SETUP.md**: LangSmith tracing configuration for debugging agent workflows
- **SUPABASE_VECTORSTORE_SETUP.md**: Supabase PostgreSQL + pgvector configuration
- **TECHNOLOGY_RAG_SETUP.md**: Technology knowledge base RAG system setup

**What goes here**: Installation guides, configuration instructions, environment setup

### `/implementation`
Implementation summaries and technical changes:
- Phase implementation summaries (PHASE1, PHASE2, etc.)
- Bug fix documentation and root cause analysis
- Feature implementation summaries
- RAG system improvements and verification
- Strategy documents (customer questions, agent improvements)

**What goes here**: Implementation notes, change summaries, feature docs, bug fixes

### `/api`
API documentation and endpoint specifications:
- Endpoint reference
- Request/response schemas
- Authentication and authorization
- WebSocket/SSE documentation

**What goes here**: API specs, endpoint docs, integration guides

### `/reports`
Generated feasibility reports and output examples:
- PDF feasibility reports
- Test case outputs
- Report templates

**What goes here**: Generated PDFs, sample reports, output templates

## Quick Links

### Key Setup Guides
1. **Start here**: `setup/LANGSMITH_SETUP.md` - Enable agent debugging
2. **Database**: `setup/SUPABASE_VECTORSTORE_SETUP.md` - Database configuration
3. **RAG System**: `setup/TECHNOLOGY_RAG_SETUP.md` - Knowledge base setup

### Recent Changes
- See `implementation/CHANGES_SUMMARY_2025-10-21.md` for latest updates
- See `implementation/CUSTOMER_QUESTIONS_STRATEGY.md` for question detection feature

## File Naming Conventions

- **Setup guides**: `<SERVICE>_SETUP.md` (e.g., `LANGSMITH_SETUP.md`)
- **Implementation docs**: `<FEATURE>_IMPLEMENTATION.md` or `PHASE<N>_*.md`
- **Verification docs**: `<FEATURE>_VERIFICATION.md` or `<FEATURE>_VERIFICATION_RESULTS.md`
- **Strategy docs**: `<FEATURE>_STRATEGY.md`
- **Reports**: `feasibility-report-<date>.pdf` or descriptive names

## Related Documentation

- **Project-level docs**: See `../../docs/`
- **Test documentation**: See `../tests/`
- **API reference**: Run backend and visit `http://localhost:8000/docs`
