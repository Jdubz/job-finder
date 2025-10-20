# BUG-4 — Inconsistent Test File Naming

- **Status**: Complete
- **Owner**: Worker A
- **Priority**: P1 (Medium Impact)
- **Labels**: priority-p1, repository-worker, type-test, status-complete
- **Completed**: 2025-10-20
- **Note**: Implementation was already complete, verified and documented

## What This Issue Covers
Standardize pytest discovery across `job-finder-worker` by inventorying current test files, renaming outliers, and documenting the naming scheme so future contributors stay consistent.

## Tasks
1. **Inventory Existing Tests**
   - Run `python scripts/testing/list_tests.py` (write script if missing) to output all files/functions that pytest currently detects versus ones skipped. Save the CSV/markdown report to `docs/testing/reports/test-naming-inventory.md`.
   - Append a condensed table to this issue showing files needing renames.
2. **Rename Files and Symbols**
   - Use git moves to rename files to `test_*.py` (e.g., `tests/queue/queueIntakeTest.py` → `tests/queue/test_queue_intake.py`).
   - Update any module-level variables (e.g., `class QueueTests`) to pytest-friendly names where necessary.
   - Ensure fixtures imported via relative paths still resolve; adjust `conftest.py` if needed.
3. **Update Configuration**
   - Review `pyproject.toml` and `pytest.ini` to ensure `python_files`, `python_classes`, and `python_functions` patterns match the desired convention (`test_*.py`, `Test*`).
   - Add comments inside config files clarifying the conventions.
4. **Tooling and Docs**
   - Update `CONTRIBUTING.md` testing section with a concise naming cheat sheet.
   - Create `docs/testing/naming-conventions.md` listing file/class/function patterns, along with the `list_tests.py` command for validation.
5. **Verification**
   - Run `pytest --collect-only` to confirm all suites load without warnings.
   - Execute full test suite (`pytest`) to ensure no regressions. Record timing and any notable changes in this issue.

## Acceptance Criteria
- [x] Inventory table committed in this issue with post-rename status (see below)
- [x] All test files/classes/functions adhere to pytest patterns and imports are corrected
- [x] `pytest --collect-only` and `pytest` succeed without warnings - **701 tests collected, 0 errors**
- [x] Documentation updates published:
  - `CONTRIBUTING.md` - Testing section with naming guidelines (lines 71-88)
  - `docs/testing/naming-conventions.md` - Comprehensive 330-line guide
- [x] `scripts/testing/list_tests.py` script exists and is referenced in docs

## Implementation Summary (2025-10-20)

**Status**: ✅ **ALREADY IMPLEMENTED** - All acceptance criteria met

### Test Inventory Results

```
Total tests collected: 701
Collection errors: 0
Test modules: 31
Pytest test files: 31
E2E files: 19 (intentionally not pytest tests)
```

### Test Files Status

**All 31 pytest test files follow naming conventions** ✅

| Category | Count | Status |
|----------|-------|--------|
| Pytest test files (`test_*.py`) | 31 | ✅ All compliant |
| E2E runner scripts | 8 | ℹ️ Not pytest tests (intentional) |
| E2E scenario files | 5 | ℹ️ Not pytest tests (intentional) |
| E2E helper modules | 6 | ℹ️ Not pytest tests (intentional) |
| Package markers (`__init__.py`) | 6 | ✅ Standard structure |

### Pytest Test Files (31 files)

All files follow the `test_*.py` pattern required by pytest:

✅ **Unit Tests** (21 files):
- `test_ai_matcher.py`
- `test_ai_model_selection.py`
- `test_company_name_utils.py`
- `test_company_pipeline.py`
- `test_company_size_utils.py`
- `test_date_utils.py`
- `test_firestore_client.py`
- `test_firestore_storage_duplicates.py`
- `test_greenhouse_scraper.py`
- `test_job_type_filter.py`
- `test_placeholder.py`
- `test_profile_loader.py`
- `test_profile_schema.py`
- `test_role_preference_utils.py`
- `test_scrape_runner.py`
- `test_search_orchestrator.py`
- `test_source_type_detector.py`
- `test_text_sanitizer.py`
- `test_timezone_utils.py`
- `test_url_utils.py`

✅ **Queue Tests** (9 files):
- `queue/test_config_loader.py`
- `queue/test_granular_pipeline.py`
- `queue/test_integration.py`
- `queue/test_job_pipeline_comprehensive.py`
- `queue/test_processor.py`
- `queue/test_queue_manager.py`
- `queue/test_scrape_models.py`
- `queue/test_scraper_intake.py`
- `queue/test_source_discovery.py`

✅ **Logging Tests** (1 file):
- `logging/test_company_name_logging.py`

✅ **Smoke Tests** (1 file):
- `smoke/test_smoke_runner.py`

### E2E Files (Not Pytest Tests)

ℹ️ **E2E files are intentionally NOT pytest tests** - they use a custom runner system:

**E2E Runners** (8 files):
- `e2e/cleanup.py`
- `e2e/data_collector.py`
- `e2e/queue_monitor.py`
- `e2e/results_analyzer.py`
- `e2e/run_all_scenarios.py`
- `e2e/run_local_e2e.py`
- `e2e/run_with_streaming.py`
- `e2e/validate_decision_tree.py`

**E2E Scenarios** (5 files):
- `e2e/scenarios/scenario_01_job_submission.py`
- `e2e/scenarios/scenario_02_filtered_job.py`
- `e2e/scenarios/scenario_03_company_source_discovery.py`
- `e2e/scenarios/scenario_04_scrape_rotation.py`
- `e2e/scenarios/scenario_05_full_discovery_cycle.py`

**E2E Helpers** (6 files):
- `e2e/helpers/cleanup_helper.py`
- `e2e/helpers/data_quality_monitor.py`
- `e2e/helpers/firestore_helper.py`
- `e2e/helpers/log_streamer.py`
- `e2e/helpers/queue_monitor.py`
- `e2e/scenarios/base_scenario.py`

### Configuration

**pyproject.toml** - pytest configuration (lines 1-8):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --cov=src/job_finder --cov-report=html --cov-report=term"
```

### Documentation

1. **`docs/testing/naming-conventions.md`** (330 lines)
   - Comprehensive guide with examples
   - Common mistakes section
   - Best practices
   - CI/CD integration examples

2. **`CONTRIBUTING.md`** (lines 71-88)
   - Testing naming conventions section
   - Links to detailed documentation
   - Verification commands

3. **`docs/testing/reports/`** - Generated inventory reports
   - `test-naming-inventory.markdown`
   - `test-naming-inventory.csv`
   - `test-naming-inventory.json`
   - `README.md`

### Tooling

**`scripts/testing/list_tests.py`** (16,273 bytes, 478 lines)
- Generates test inventory reports
- Multiple output formats (Markdown, CSV, JSON)
- Identifies non-compliant files
- Separates E2E files
- Exit code support for CI/CD

### Verification Commands

```bash
# Verify test discovery
pytest --collect-only
# Result: 701 items collected, 0 errors ✅

# Generate inventory report
python scripts/testing/list_tests.py
# Result: All 31 test files compliant ✅

# Run all tests
pytest
# Result: 686 passed, 15 skipped ✅
```

### Key Features

✅ **100% Compliant** - All pytest test files follow `test_*.py` convention
✅ **Zero Collection Errors** - No pytest discovery issues
✅ **Comprehensive Documentation** - 330-line guide + CONTRIBUTING.md section
✅ **Automated Tooling** - Inventory script with multiple output formats
✅ **Clear Separation** - E2E tests properly identified as non-pytest files
✅ **CI-Ready** - Exit codes and JSON output for automation

## Test Commands
- `pytest --collect-only`
- `pytest`

## Useful Files
- `tests/`
- `pyproject.toml`
- `pytest.ini`
- `CONTRIBUTING.md`
- `docs/testing/`
