# Test Naming Conventions

This document defines the naming conventions for test files, classes, and functions in the Job Finder Worker project.

## Overview

The project uses **pytest** as its primary test framework. All test files must follow pytest's discovery patterns to ensure they are automatically detected and executed.

## Naming Patterns

### Test Files

**Pattern:** `test_*.py`

All pytest test files MUST start with `test_` and end with `.py`.

✅ **Correct Examples:**
- `test_ai_matcher.py`
- `test_queue_manager.py`
- `test_integration.py`

❌ **Incorrect Examples:**
- `ai_matcher_test.py` (suffix instead of prefix)
- `aiMatcherTest.py` (camelCase, suffix)
- `tests_ai_matcher.py` (plural 'tests')

### Test Classes

**Pattern:** `Test*` or `*Tests`

Test classes should start with `Test` (preferred) or end with `Tests`.

✅ **Correct Examples:**
```python
class TestAIJobMatcher:
    """Test AI job matcher functionality."""
    pass

class TestQueueWorkflow:
    """Test queue workflow."""
    pass
```

❌ **Incorrect Examples:**
```python
class AIMatcherTest:  # Wrong: suffix instead of prefix
    pass

class QueueTests:  # Acceptable but not preferred - use TestQueue
    pass
```

### Test Functions

**Pattern:** `test_*`

All test functions MUST start with `test_`.

✅ **Correct Examples:**
```python
def test_matcher_initialization():
    """Test matcher initialization."""
    pass

def test_analyze_match_success():
    """Test successful match analysis."""
    pass
```

❌ **Incorrect Examples:**
```python
def matcher_test():  # Wrong: missing 'test_' prefix
    pass

def testMatcherInit():  # Wrong: camelCase
    pass
```

## pytest Configuration

The project's pytest configuration is defined in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "-v --cov=src/job_finder --cov-report=html --cov-report=term"
```

**Key Settings:**
- `testpaths`: Only search for tests in the `tests/` directory
- `python_files`: Only collect files matching `test_*.py`
- `python_functions`: Only collect functions matching `test_*`

## Directory Structure

```
tests/
├── __init__.py                      # Package marker
├── test_*.py                        # Unit test files
├── conftest.py                      # Pytest fixtures (if needed)
├── queue/                           # Subdirectory for queue tests
│   ├── __init__.py
│   └── test_*.py
└── e2e/                             # E2E tests (separate execution model)
    ├── run_all_scenarios.py         # E2E runner (not a pytest test)
    ├── scenarios/
    │   └── scenario_*.py            # E2E scenarios (not pytest tests)
    └── helpers/
        └── *_helper.py              # E2E helper modules
```

## E2E Tests

**Important:** Files in `tests/e2e/` are **NOT** pytest tests. They use a custom runner system.

E2E tests are executed via:
```bash
python tests/e2e/run_all_scenarios.py
```

E2E files do NOT need to follow the `test_*.py` pattern because they are not discovered by pytest.

## Validation

### Verify Test Discovery

Run pytest collection to see which tests will be executed:

```bash
# Collect all tests without running them
pytest --collect-only

# Collect tests from a specific file
pytest --collect-only tests/test_ai_matcher.py

# Count total tests
pytest --collect-only -q
```

### Generate Test Inventory

Use the test inventory script to generate a report of all test files:

```bash
# Generate markdown report (default)
python scripts/testing/list_tests.py

# Generate all formats (markdown, CSV, JSON)
python scripts/testing/list_tests.py --format all

# Save to specific file
python scripts/testing/list_tests.py --output report.md
```

The inventory script will:
- Show all test files discovered by pytest
- Identify files that don't follow naming conventions
- List E2E files separately (they're not pytest tests)
- Report any collection errors

## Common Mistakes

### 1. Using Suffix Instead of Prefix

❌ **Wrong:**
```python
# File: ai_matcher_test.py
class AIMatcherTest:
    def test_something(self):
        pass
```

✅ **Correct:**
```python
# File: test_ai_matcher.py
class TestAIMatcher:
    def test_something(self):
        pass
```

### 2. Using camelCase

❌ **Wrong:**
```python
def testAIMatcherInit():
    pass
```

✅ **Correct:**
```python
def test_ai_matcher_init():
    pass
```

### 3. Missing test_ Prefix

❌ **Wrong:**
```python
def verify_matcher_works():
    """This won't be discovered by pytest."""
    pass
```

✅ **Correct:**
```python
def test_matcher_works():
    """This will be discovered by pytest."""
    pass
```

## Best Practices

### 1. Descriptive Names

Use descriptive names that explain what is being tested:

```python
# ✅ Good - clear what's being tested
def test_matcher_returns_high_score_for_perfect_match():
    pass

# ❌ Bad - too vague
def test_matcher():
    pass
```

### 2. Organize by Module

Group related tests in the same file:

```python
# File: test_ai_matcher.py
class TestAIMatcherInit:
    """Tests for initialization."""
    
    def test_init_stores_config(self):
        pass
    
    def test_init_with_defaults(self):
        pass

class TestAIMatcherAnalysis:
    """Tests for match analysis."""
    
    def test_analyze_match_success(self):
        pass
    
    def test_analyze_match_handles_errors(self):
        pass
```

### 3. Use Subdirectories

Organize tests in subdirectories matching the source code structure:

```
src/job_finder/
├── ai/
│   └── matcher.py
└── queue/
    └── manager.py

tests/
├── test_ai_matcher.py       # Could be in tests/ai/test_matcher.py
└── queue/
    └── test_queue_manager.py
```

### 4. Keep E2E Tests Separate

E2E integration tests should live in `tests/e2e/` and use their own runner:

```
tests/
├── test_*.py                # Unit tests (pytest)
└── e2e/                     # Integration tests (custom runner)
    ├── run_all_scenarios.py
    └── scenarios/
        └── scenario_*.py
```

## Continuous Integration

### Pre-commit Hook

Add a pre-commit hook to validate test naming:

```bash
#!/bin/bash
# .githooks/pre-commit

# Run test inventory to verify naming
python scripts/testing/list_tests.py --format json > /tmp/test-inventory.json

# Check for naming violations (would be in 'other' category)
if grep -q '"other": \[' /tmp/test-inventory.json; then
    echo "❌ ERROR: Test files found that don't follow naming conventions"
    python scripts/testing/list_tests.py
    exit 1
fi

echo "✅ All test files follow naming conventions"
```

### CI Pipeline

Add to GitHub Actions workflow:

```yaml
- name: Validate Test Naming
  run: |
    python scripts/testing/list_tests.py --format all
    pytest --collect-only
```

## References

- [pytest Documentation - Test Discovery](https://docs.pytest.org/en/stable/goodpractices.html#test-discovery)
- [pytest Configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- Project `pyproject.toml` - pytest configuration section

## Questions?

If you have questions about test naming conventions, please:
1. Check this document
2. Run `python scripts/testing/list_tests.py` to see examples
3. Open an issue with the "question" label
