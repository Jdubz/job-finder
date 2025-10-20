# Test Naming Inventory Report

**Generated:** 2025-10-20 07:30:47

## Summary

- **Total Tests Collected:** 501
- **Collection Errors:** 7
- **Test Modules:** 21

## Test Files (Following pytest Pattern)

**Count:** 28 files

All files follow the `test_*.py` naming convention required by pytest.

| File Path | Status |
|-----------|--------|
| `queue/test_config_loader.py` | ✅ Pytest Discoverable |
| `queue/test_granular_pipeline.py` | ✅ Pytest Discoverable |
| `queue/test_integration.py` | ✅ Pytest Discoverable |
| `queue/test_job_pipeline_comprehensive.py` | ✅ Pytest Discoverable |
| `queue/test_processor.py` | ✅ Pytest Discoverable |
| `queue/test_queue_manager.py` | ✅ Pytest Discoverable |
| `queue/test_scrape_models.py` | ✅ Pytest Discoverable |
| `queue/test_scraper_intake.py` | ✅ Pytest Discoverable |
| `queue/test_source_discovery.py` | ✅ Pytest Discoverable |
| `test_ai_matcher.py` | ✅ Pytest Discoverable |
| `test_ai_model_selection.py` | ✅ Pytest Discoverable |
| `test_company_name_utils.py` | ✅ Pytest Discoverable |
| `test_company_pipeline.py` | ✅ Pytest Discoverable |
| `test_company_size_utils.py` | ✅ Pytest Discoverable |
| `test_date_utils.py` | ✅ Pytest Discoverable |
| `test_firestore_client.py` | ✅ Pytest Discoverable |
| `test_greenhouse_scraper.py` | ✅ Pytest Discoverable |
| `test_job_type_filter.py` | ✅ Pytest Discoverable |
| `test_placeholder.py` | ✅ Pytest Discoverable |
| `test_profile_loader.py` | ✅ Pytest Discoverable |
| `test_profile_schema.py` | ✅ Pytest Discoverable |
| `test_role_preference_utils.py` | ✅ Pytest Discoverable |
| `test_scrape_runner.py` | ✅ Pytest Discoverable |
| `test_search_orchestrator.py` | ✅ Pytest Discoverable |
| `test_source_type_detector.py` | ✅ Pytest Discoverable |
| `test_text_sanitizer.py` | ✅ Pytest Discoverable |
| `test_timezone_utils.py` | ✅ Pytest Discoverable |
| `test_url_utils.py` | ✅ Pytest Discoverable |

## Helper Files

Standard pytest helper files (not collected as tests).

| File Path | Purpose |
|-----------|---------|
| `__init__.py` | Package marker |
| `e2e/helpers/__init__.py` | Package marker |
| `e2e/scenarios/__init__.py` | Package marker |
| `queue/__init__.py` | Package marker |

## E2E Test Files

E2E tests use a custom runner system and are NOT collected by pytest.
These are integration test scripts with their own execution model.

### E2E Runners

**Count:** 8 files

| File Path | Description |
|-----------|-------------|
| `e2e/cleanup.py` | E2E test runner script |
| `e2e/data_collector.py` | E2E test runner script |
| `e2e/queue_monitor.py` | E2E test runner script |
| `e2e/results_analyzer.py` | E2E test runner script |
| `e2e/run_all_scenarios.py` | E2E test runner script |
| `e2e/run_local_e2e.py` | E2E test runner script |
| `e2e/run_with_streaming.py` | E2E test runner script |
| `e2e/validate_decision_tree.py` | E2E test runner script |

### E2E Scenarios

**Count:** 5 files

| File Path | Description |
|-----------|-------------|
| `e2e/scenarios/scenario_01_job_submission.py` | E2E scenario definition |
| `e2e/scenarios/scenario_02_filtered_job.py` | E2E scenario definition |
| `e2e/scenarios/scenario_03_company_source_discovery.py` | E2E scenario definition |
| `e2e/scenarios/scenario_04_scrape_rotation.py` | E2E scenario definition |
| `e2e/scenarios/scenario_05_full_discovery_cycle.py` | E2E scenario definition |

### E2E Helpers

**Count:** 6 files

| File Path | Description |
|-----------|-------------|
| `e2e/helpers/cleanup_helper.py` | E2E helper module |
| `e2e/helpers/data_quality_monitor.py` | E2E helper module |
| `e2e/helpers/firestore_helper.py` | E2E helper module |
| `e2e/helpers/log_streamer.py` | E2E helper module |
| `e2e/helpers/queue_monitor.py` | E2E helper module |
| `e2e/scenarios/base_scenario.py` | E2E helper module |

## Collection Errors

Files that failed to import during collection (typically due to missing dependencies).

| File Path | Note |
|-----------|------|
| `tests/queue/test_granular_pipeline.py ____________` | Import error (unrelated to naming) |
| `tests/queue/test_job_pipeline_comprehensive.py ________` | Import error (unrelated to naming) |
| `tests/queue/test_processor.py ________________` | Import error (unrelated to naming) |
| `tests/queue/test_source_discovery.py _____________` | Import error (unrelated to naming) |
| `tests/test_company_pipeline.py ________________` | Import error (unrelated to naming) |
| `tests/test_scrape_runner.py _________________` | Import error (unrelated to naming) |
| `tests/test_search_orchestrator.py ______________` | Import error (unrelated to naming) |

## Conclusions

### ✅ All Pytest Test Files Follow Naming Conventions

- All 28 test files follow the `test_*.py` pattern
- Pytest successfully discovers and collects tests from these files
- No renaming is required for pytest test files

### E2E Tests Are Not Pytest Tests

- E2E test files in `tests/e2e/` are integration test runners
- They have their own execution model via `run_all_scenarios.py`
- They are NOT intended to be discovered by pytest
- Their current naming is appropriate for their purpose

### Collection Errors Are Unrelated to Naming

- 7 import errors exist but are caused by missing dependencies, not naming issues

### Recommendations

1. ✅ **No renaming needed** - All files follow correct conventions
2. 📝 **Document conventions** - Add clear documentation for future contributors
3. 🔧 **Add validation** - Use this script in CI to catch future naming issues
4. 📚 **Update CONTRIBUTING.md** - Include naming conventions in contribution guide