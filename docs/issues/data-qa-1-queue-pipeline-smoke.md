# DATA-QA-1 — Queue Pipeline Smoke & Data Integrity Check

- **Status**: Todo
- **Owner**: Worker A
- **Priority**: P1 (High Impact)
- **Labels**: priority-p1, repository-worker, type-testing, status-todo

## What This Issue Covers
Create an automated smoke test that pushes representative jobs through the worker pipeline, validates Cloud Function responses, and checks Firestore for data quality issues. Everything required (fixtures, scripts, docs) must live in `job-finder-worker` so others can re-run it.

## Tasks
1. **Design the Scenario Set**
   - Define at least five representative job postings (remote, hybrid, onsite, global company, high-seniority). Store fixtures under `tests/fixtures/smoke_jobs/` as JSON.
   - Document criteria in this issue and in `docs/testing/queue-smoke.md` so future updates know why each case exists.
2. **Build Smoke Runner**
   - Implement `scripts/smoke/queue_pipeline_smoke.py` that:
     - Loads fixtures.
     - Uses existing ingestion code (`src/job_finder/queue/scraper_intake.py`) to enqueue jobs.
     - Polls Firestore (via `google-cloud-firestore`) until each job reaches a terminal state.
     - Outputs a structured report containing status, processing time, scoring values, and generated document IDs.
   - Support flags `--env staging|local` and `--dry-run` for safe execution.
3. **Validation Checks**
   - Within the smoke runner, assert:
     - No duplicate normalized URLs (reuse utility from BUG-1).
     - Required scoring fields (`relevance_score`, `timezone_score`, etc.) are present.
     - For generator-enabled jobs, confirm document references exist.
   - Fail fast with descriptive errors and include remediation hints in the report.
4. **Automation Hooks**
   - Add a Make target (`make smoke-queue`) and npm/pip entrypoint (`poetry run smoke-queue` if using poetry) documented in `Makefile`.
   - Create GitHub Actions workflow `smoke-queue.yml` that can be manually triggered. The workflow should run with `USE_AI_STUBS=true` to avoid paid calls.
   - Ensure secrets are read from environment variables documented in `docs/testing/queue-smoke.md` (no plaintext secrets committed).
5. **Reporting**
   - Have the script write markdown and JSON summaries to `test_results/queue_smoke/<timestamp>/`. Keep directory gitignored but record paths and sample outputs in this issue.
   - Include instructions for attaching sanitized excerpts to issue comments when sharing results.

## Acceptance Criteria
- [ ] Smoke fixtures stored in `tests/fixtures/smoke_jobs/` with documentation.
- [ ] `scripts/smoke/queue_pipeline_smoke.py` runs end-to-end, validating duplicates and scoring fields.
- [ ] Make/CLI commands (`make smoke-queue`, `python scripts/smoke/queue_pipeline_smoke.py --env staging`) documented and functioning.
- [ ] GitHub Actions workflow defined for manual runs with stubbed AI dependencies.
- [ ] Issue updated with latest smoke run summary (pass/fail, timestamp, data quality notes).

## Test Commands
- `pytest tests/smoke` (add tests verifying smoke helper functions).
- `python scripts/smoke/queue_pipeline_smoke.py --env local --dry-run`
- `make smoke-queue`

## Useful Files
- `src/job_finder/queue/scraper_intake.py`
- `scripts/smoke/queue_pipeline_smoke.py`
- `tests/fixtures/smoke_jobs/`
- `docs/testing/queue-smoke.md`
