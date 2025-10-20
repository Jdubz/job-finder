# BUG-1 — Duplicate Jobs in Matches

- **Status**: Todo
- **Owner**: Worker A
- **Priority**: P1 (High Impact)
- **Labels**: priority-p1, repository-worker, type-bug, status-todo

## What This Issue Covers
Eliminate duplicate job matches by normalizing URLs, adding Firestore safeguards, and cleaning existing data. Everything happens within `job-finder-worker` so future contributors can repeat the process.

## Tasks
1. **Document Current Behavior**
   - Run `python scripts/analytics/report_duplicate_matches.py --env staging` (create script if missing) to capture current duplicates grouped by normalized URL guess. Save the report to `test_results/duplicates/before.json` (gitignored) and summarize counts in this issue.
   - Review `src/job_finder/queue/scraper_intake.py` to note where URLs enter the pipeline and how IDs are generated.
2. **Implement Normalization Utility**
   - Add `src/job_finder/utils/url_normalizer.py` exposing `normalize_job_url(raw_url: str) -> NormalizedUrl` using `urllib.parse`. Handle lowercasing, removing tracking params (utm, ref), stripping trailing slashes, and collapsing `www.` subdomains.
   - Write unit tests under `tests/utils/test_url_normalizer.py` covering common edge cases and international domain names.
3. **Integrate Safeguards**
   - Update intake pipeline (`src/job_finder/queue/scraper_intake.py`) to store both raw and normalized URLs. Before writing to Firestore, query for existing documents with the same normalized value using the `job-matches` collection index.
   - Add structured logging when a duplicate is skipped (include normalized URL and existing doc ID) so observability dashboards can track it.
4. **Historical Cleanup**
   - Extend `scripts/database/cleanup_job_matches.py` to:
     - Normalize all existing documents.
     - Identify duplicates keeping the highest ranked or most recent entry.
     - Produce a dry-run summary (`--dry-run`) saved to `test_results/duplicates/dry-run.md` and a final summary after execution.
   - Document usage instructions at the top of the script (comment) and in `docs/operations/duplicate-cleanup.md` (new doc).
5. **Verification**
   - Re-run the analytics script post-cleanup and update this issue with before/after counts.
   - Add an assertion to the DATA-QA-1 smoke test (once available) ensuring duplicates remain zero; note coordination requirement in that issue.

## Acceptance Criteria
- [ ] `normalize_job_url` utility implemented with comprehensive tests.
- [ ] Intake pipeline writes normalized URLs and skips duplicates with structured logs.
- [ ] Cleanup script executed against staging; results summarized in this issue (counts before/after).
- [ ] `docs/operations/duplicate-cleanup.md` explains how to rerun detection and cleanup.
- [ ] `pytest` suite passes (`pytest tests/utils/test_url_normalizer.py tests/queue/test_scraper_intake.py`).

## Test Commands
- `pytest tests/utils/test_url_normalizer.py`
- `pytest tests/queue/test_scraper_intake.py`
- `pytest`

## Useful Files
- `src/job_finder/queue/scraper_intake.py`
- `src/job_finder/utils/url_normalizer.py`
- `scripts/database/cleanup_job_matches.py`
- `docs/operations/duplicate-cleanup.md`
