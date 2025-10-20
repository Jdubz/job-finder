# Test Naming Inventory Reports

This directory contains automatically generated reports of the test file inventory for the Job Finder Worker project.

## Reports

### test-naming-inventory.markdown
Human-readable markdown report showing:
- Summary of test files by category
- Complete list of pytest test files
- E2E test files (not pytest tests)
- Collection errors and their causes
- Conclusions and recommendations

**Best for:** Code review, documentation, GitHub issues

### test-naming-inventory.csv
Comma-separated values format with columns:
- File Path
- Category
- Pytest Discoverable
- Status

**Best for:** Spreadsheet analysis, importing into tools, data processing

### test-naming-inventory.json
Machine-readable JSON format with:
- Collection results (test counts, errors)
- File categorization
- Timestamp of generation

**Best for:** Automated tooling, CI/CD pipelines, programmatic analysis

## Generating Reports

To regenerate these reports, run:

```bash
# Generate all formats
python scripts/testing/list_tests.py --format all

# Generate specific format
python scripts/testing/list_tests.py --format markdown
python scripts/testing/list_tests.py --format csv
python scripts/testing/list_tests.py --format json

# Output to custom location
python scripts/testing/list_tests.py --output custom-report.md
```

## When to Regenerate

Regenerate these reports when:
- Adding new test files
- Reorganizing test directory structure
- Verifying naming conventions before PR submission
- Investigating test discovery issues
- Updating documentation

## CI Integration

These reports can be generated automatically in CI:

```yaml
- name: Generate Test Inventory
  run: python scripts/testing/list_tests.py --format all
  
- name: Upload Reports as Artifacts
  uses: actions/upload-artifact@v3
  with:
    name: test-inventory
    path: docs/testing/reports/
```

## Report Contents

### Categories Tracked

1. **Pytest Test Files**: Files following `test_*.py` pattern
2. **Helper Files**: `__init__.py`, `conftest.py`
3. **E2E Runners**: E2E test orchestration scripts
4. **E2E Scenarios**: E2E test scenario definitions
5. **E2E Helpers**: E2E utility modules
6. **Other**: Any uncategorized Python files

### Status Indicators

- ✅ **Pytest Discoverable**: File follows convention and is collected by pytest
- ✅ **Standard Helper**: Expected helper file (not a test)
- ✅ **Not a Pytest Test**: E2E file with separate execution model
- ⚠️ **Review Needed**: File doesn't fit expected categories

## Related Documentation

- [Testing Naming Conventions](../naming-conventions.md) - Detailed naming standards
- [CONTRIBUTING.md](../../../CONTRIBUTING.md) - Contributing guidelines
- [pytest Documentation](https://docs.pytest.org/) - pytest test discovery

## Last Generated

Check the timestamp in each report file to see when it was last generated.

To see current status:
```bash
python scripts/testing/list_tests.py 2>&1 | grep -E "Total|Collection|Test modules"
```
