# Documentation Directory Structure

This directory contains project-level documentation for the Oxytec Multi-Agent Feasibility Platform.

## Directory Organization

### `/architecture`
System architecture, design decisions, and technical specifications:
- Agent workflow design and interactions
- UI/UX flow diagrams
- Model selection rationale
- Technology stack decisions

**What goes here**: Architecture diagrams, design docs, technical decision records

### `/development`
Development guides, code reviews, and prompt engineering:
- Code review reports and fixes
- Prompt engineering reviews and updates
- Development best practices
- Refactoring summaries

**What goes here**: Code reviews, prompt updates, development guidelines

### `/evaluation`
Testing strategies, evaluation frameworks, and results:
- Agent evaluation strategies (EXTRACTOR, PLANNER, etc.)
- Quality assessment frameworks
- Evaluation results and analysis
- Testing methodology

**What goes here**: Evaluation strategies, test results, quality analysis

### `/examples`
Example outputs, sample data, and reference materials:
- Example agent outputs (JSON)
- Sample feasibility reports (PDF)
- Test inquiry documents
- Screenshots and visual references
- Scope definitions and configurations

**What goes here**: Example files, sample data, reference PDFs, screenshots

## File Naming Conventions

- **Date-stamped docs**: `TOPIC_YYYY-MM-DD.md` (e.g., `CODE_REVIEW_2025-10-21.md`)
- **Version-controlled docs**: `TOPIC_vN.md` (e.g., `EVALUATION_STRATEGY_v2.md`)
- **General docs**: `TOPIC.md` (e.g., `ARCHITECTURE.md`)
- **Examples**: `example_<agent_name>.json` (e.g., `example_extractor.json`)

## Related Documentation

- **Backend-specific docs**: See `backend/docs/`
- **Frontend docs**: See `frontend/README.md`
- **API documentation**: Available at `http://localhost:8000/docs` when backend is running
