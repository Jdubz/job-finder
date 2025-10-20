# BUG-4 — Inconsistent Test File Naming

- **Status**: Todo
- **Owner**: Worker A
- **Priority**: P1 (Medium Impact)
- **Labels**: priority-p1, repository-worker, type-test, status-todo

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
- [ ] Inventory table committed in this issue with post-rename status.
- [ ] All test files/classes/functions adhere to pytest patterns and imports are corrected.
- [ ] `pytest --collect-only` and `pytest` succeed without warnings.
- [ ] Documentation updates published (`CONTRIBUTING.md`, `docs/testing/naming-conventions.md`).
- [ ] `scripts/testing/list_tests.py` (or equivalent) exists and is referenced in docs.

## Test Commands
- `pytest --collect-only`
- `pytest`

## Useful Files
- `tests/`
- `pyproject.toml`
- `pytest.ini`
- `CONTRIBUTING.md`
- `docs/testing/`
