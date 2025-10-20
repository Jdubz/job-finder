# BUG-2 — Timezone Detection for Global Companies

- **Status**: Todo
- **Owner**: Worker A
- **Priority**: P1 (High Impact)
- **Labels**: priority-p1, repository-worker, type-bug, status-todo

## What This Issue Covers
Fix timezone scoring for globally distributed companies by introducing configuration-driven overrides, updating detection logic, and documenting the workflow so contributors can maintain it from `job-finder-worker` alone.

## Tasks
1. **Collect Problem Cases**
   - Use `python scripts/analytics/timezone_false_penalties.py --env staging` (create script if needed) to export postings where timezone score < 0 for companies with `remote` descriptors. Save results to `test_results/timezone/before.csv` (gitignored) and summarize counts in this issue.
2. **Build Global Company Registry**
   - Create `config/company/timezone_overrides.json` containing:
     - Exact company names with `"timezone":"unknown"` default.
     - Optional regex/wildcard patterns for holdings.
     - Metadata fields (`source`, `last_updated`).
   - Add loader in `src/job_finder/config/timezone_overrides.py` with caching and validation (raise if schema invalid).
   - Document update procedure in `docs/config/timezone-overrides.md`.
3. **Update Detection Logic**
   - Modify `src/job_finder/utils/timezone_utils.py` to check overrides before inferring timezone. When override present and job lacks explicit location, return `Timezone.UNKNOWN`.
   - Ensure remote descriptors like “Global” or “Anywhere” also force unknown if company in override list.
   - Adjust scoring pipeline in `src/job_finder/scoring/timezone_score.py` so `UNKNOWN` no longer penalizes flagged companies.
4. **Testing**
   - Add unit tests in `tests/utils/test_timezone_utils.py` covering override hits, misses, and explicit locations.
   - Add regression test in `tests/scoring/test_timezone_score.py` verifying scores remain neutral for overridden companies.
   - Include fixture data under `tests/fixtures/timezone/` to keep tests deterministic.
5. **Verification & Reporting**
   - Re-run the analytics script post-change and attach summary to this issue (counts before/after, sample entries).
   - Coordinate with Worker B to ensure UI messaging matches (note cross-reference in FE issue if adjustments needed).

## Acceptance Criteria
- [ ] Override configuration file added with schema validation.
- [ ] Timezone helper and scoring pipeline respect overrides and avoid penalties.
- [ ] Unit/regression tests added and passing (`pytest`).
- [ ] Documentation (`docs/config/timezone-overrides.md`) explains maintenance workflow.
- [ ] Issue updated with before/after analytics results.

## Test Commands
- `pytest tests/utils/test_timezone_utils.py`
- `pytest tests/scoring/test_timezone_score.py`
- `pytest`

## Useful Files
- `src/job_finder/utils/timezone_utils.py`
- `src/job_finder/scoring/timezone_score.py`
- `config/company/timezone_overrides.json`
- `tests/utils/` and `tests/scoring/`
