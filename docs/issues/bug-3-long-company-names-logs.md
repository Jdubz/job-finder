# BUG-3 — Long Company Names Truncated in Logs

- **Status**: Todo
- **Owner**: Worker A
- **Priority**: P1 (Medium Impact)
- **Labels**: priority-p1, repository-worker, type-bug, status-todo

## What This Issue Covers
Ensure structured logs retain full company names while preserving readable console output. All work happens inside `job-finder-worker` and should leave behind tests plus documentation for future changes.

## Tasks
1. **Audit Current Logging Pipeline**
   - Inspect `src/job_finder/logging/config.py` and `src/job_finder/logging/formatters.py` to identify where company names are truncated (likely via `textwrap.shorten` or slicing).
   - Run `python scripts/logging/sample_logs.py --company "Very Long Company Name…"` (create script if missing) to reproduce truncation and capture output in `test_results/logging/before.json`.
2. **Enhance Structured Payloads**
   - Update the JSON formatter to emit two fields: `company_name` (full string) and `company_name_display` (optional trimmed version for console).
   - Introduce a helper `format_company_name(company: str)` in `src/job_finder/logging/helpers.py` that returns both values. Ensure logger calls use this helper.
3. **Console-Friendly Rendering**
   - Adjust console handler (if using `rich` or standard logging) to display truncated names with ellipsis while logging full names in structured outputs.
   - Add configuration flag in `config/logging.yaml` to control max length, defaulting to 80 characters.
4. **Testing**
   - Create unit tests under `tests/logging/test_company_name_logging.py` verifying that:
     - Structured output retains full names.
     - Console output uses ellipsis but never throws exceptions with unicode.
     - Helper respects configurable max length.
   - Add snapshot or golden file tests stored in `tests/logging/__snapshots__/`.
5. **Verification**
   - Run `python run_job_search.py --dry-run --limit 5` to generate logs, export them from the configured sink (or capture stdout) and store sample in `test_results/logging/after.json` (gitignored). Summarize results in this issue.
   - Update `docs/observability/logging.md` describing new fields and how to adjust display length.

## Acceptance Criteria
- [ ] Logging helper outputs both full and display-friendly company name fields.
- [ ] No truncation occurs in structured logs; console output remains readable.
- [ ] Unit tests and snapshots confirm behavior for long/unicode names.
- [ ] Documentation updated and sample logs showing before/after behavior linked in this issue.
- [ ] `pytest` suite passes (`pytest tests/logging/test_company_name_logging.py`).

## Test Commands
- `pytest tests/logging/test_company_name_logging.py`
- `pytest`
- `python run_job_search.py --dry-run --limit 5`

## Useful Files
- `src/job_finder/logging/`
- `config/logging.yaml`
- `tests/logging/`
- `docs/observability/logging.md`
