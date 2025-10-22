# Test Suite Documentation

Comprehensive test suite for the Oxytec Multi-Agent Feasibility Platform backend.

## Directory Organization

### `/unit`
Unit tests for individual services, utilities, and functions:
- Service layer tests (LLMService, DocumentService, RAGService, etc.)
- Utility function tests
- Model validation tests
- Database model tests

**Run unit tests**:
```bash
cd backend
source .venv/bin/activate
python3 -m pytest tests/unit/ -v
```

**What goes here**: Tests for isolated functions/classes with mocked dependencies

### `/integration`
Integration tests for agent nodes and workflows:
- Individual agent node tests (EXTRACTOR, PLANNER, SUBAGENT, etc.)
- Multi-node workflow tests
- Service integration tests (LLM + RAG, Document + DB)
- API endpoint integration tests

**Run integration tests**:
```bash
cd backend
source .venv/bin/activate
python3 -m pytest tests/integration/ -v
```

**What goes here**: Tests that verify multiple components working together

### `/e2e`
End-to-end tests for complete workflows:
- Full session lifecycle tests (upload → extraction → planning → execution → reporting)
- Real document processing tests
- API endpoint + background task tests
- Performance and timing tests

**Run e2e tests**:
```bash
cd backend
source .venv/bin/activate
python3 -m pytest tests/e2e/ -v
```

**What goes here**: Tests that simulate real user workflows from start to finish

### `/evaluation`
Evaluation frameworks for measuring agent quality:

#### `/evaluation/extractor`
EXTRACTOR agent evaluation framework:
- **Layer 1 tests**: Document parsing quality (PDF, Excel, DOCX)
- **Layer 2 tests**: LLM interpretation quality (units, values, structure)
- **Ground truth management**: Reference outputs for comparison
- **Metrics**: Text similarity, accuracy, completeness scores

**Run extractor evaluation**:
```bash
cd backend
source .venv/bin/activate

# Run specific test file
python3 tests/evaluation/extractor/test_single_file.py <filename.xlsx>

# Run all Layer 2 tests (LLM interpretation)
python3 -m pytest tests/evaluation/extractor/layer2_llm_interpretation/ -v

# Run all Layer 1 tests (document parsing)
python3 -m pytest tests/evaluation/extractor/layer1_document_parsing/ -v

# Run full evaluation suite
python3 -m pytest tests/evaluation/extractor/ -v --ignore=tests/evaluation/extractor/test_single_file.py
```

**Documentation**:
- `evaluation/extractor/README.md` - Framework overview
- `evaluation/extractor/QUICKSTART.md` - Quick start guide
- `evaluation/extractor/RESULTS_FIRST_RUN.md` - Baseline evaluation results
- `evaluation/extractor/IMPROVEMENTS_IMPLEMENTED_2025-10-22.md` - Recent improvements

**What goes here**: Quality measurement frameworks, evaluation scripts, ground truth data

## Running Tests

### Prerequisites
Always use the virtual environment and python3:

```bash
cd backend
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Common Test Commands

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run tests in a specific directory
python3 -m pytest tests/unit/ -v
python3 -m pytest tests/integration/ -v
python3 -m pytest tests/e2e/ -v

# Run tests matching a pattern
python3 -m pytest tests/ -k "test_extractor" -v

# Run with coverage
python3 -m pytest tests/ --cov=app --cov-report=html

# Run specific test file
python3 -m pytest tests/unit/test_llm_service.py -v

# Run and show print statements
python3 -m pytest tests/ -v -s
```

### Test Markers

Tests can be marked with custom markers for selective execution:

```bash
# Run only fast tests
python3 -m pytest -m "fast" -v

# Run only slow tests
python3 -m pytest -m "slow" -v

# Skip integration tests
python3 -m pytest -m "not integration" -v
```

## Writing Tests

### File Naming Conventions

- **Unit tests**: `test_<module_name>.py` (e.g., `test_llm_service.py`)
- **Integration tests**: `test_<feature>_integration.py` (e.g., `test_extractor_integration.py`)
- **E2E tests**: `test_<workflow>_e2e.py` (e.g., `test_full_session_e2e.py`)
- **Evaluation scripts**: `test_<aspect>.py` (e.g., `test_unit_parsing.py`)

### Test Function Naming

```python
# Unit tests - test specific behavior
def test_llm_service_returns_structured_json():
    ...

# Integration tests - test component interaction
def test_extractor_node_with_document_service():
    ...

# E2E tests - test user workflow
def test_full_session_creates_feasibility_report():
    ...
```

### Using Fixtures

Common fixtures are defined in `conftest.py` files at each level:

```python
import pytest

@pytest.fixture
async def mock_llm_response():
    return {"extracted_facts": {...}}

@pytest.mark.asyncio
async def test_extractor_node(mock_llm_response):
    # Test uses fixture
    ...
```

### Test Organization Best Practices

1. **Unit tests**: Mock all external dependencies (LLM API, database, file system)
2. **Integration tests**: Use real services but with test data
3. **E2E tests**: Use complete test fixtures (real files, real workflow)
4. **Evaluation tests**: Use ground truth data and scoring metrics

## Test Data

Test documents and ground truth data are stored in:
- `tests/evaluation/extractor/test_documents/` - Test PDFs, Excel files, etc.
- `tests/evaluation/extractor/test_documents/ground_truth/` - Expected outputs

## Continuous Integration

Tests should pass before merging:

```bash
# Full CI check
cd backend
source .venv/bin/activate
python3 -m pytest tests/ -v --cov=app
black app/
ruff check app/
mypy app/
```

## Related Documentation

- **Evaluation results**: See evaluation framework READMEs in each evaluation subdirectory
- **Implementation docs**: See `../docs/implementation/`
- **Setup guides**: See `../docs/setup/`
