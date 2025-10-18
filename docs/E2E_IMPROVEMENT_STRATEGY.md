# E2E Test Suite: Complete Improvement Strategy

**Created:** October 18, 2025  
**Status:** Ready for Implementation  
**Target:** Improve staging environment E2E test reliability and accuracy

---

## Quick Summary of Issues & Solutions

### Issue #1: Job Deduplication Failures

**Problem:** Repeated scans create duplicate job entries. Same job URL appears multiple times in job-matches collection.

**Root Cause:** 
- `job_exists()` performs individual Firestore query per job (N+1 problem)
- No URL normalization (trailing slashes, params, case sensitivity)
- No caching of recent lookups

**Solutions:**
1. Batch URL checking with `batch_check_exists()` → Reduce 50 queries to ~5
2. URL normalization with `normalize_url()` → Handle formatting variations
3. Checksum-based lookups using `urlHash` field → Faster queries
4. Deduplication cache → Avoid repeated Firestore reads

**Impact:** Duplicates eliminated, 90% faster dedup checks

---

### Issue #2: Source Rotation Failures

**Problem:** Sources not rotated fairly. Some companies always scraped, others never. E2E tests can't verify rotation is working.

**Root Cause:**
- Incomplete timestamp tracking (`scraped_at` sometimes null)
- Rotation algorithm ignores source health and priority
- No company fairness mechanism
- Test verification uses unreliable timestamp comparison

**Solutions:**
1. Comprehensive health tracking → Track `lastScrapedAt`, success/failure counts
2. Improved rotation with scoring → Health × Tier × Age × Company Fairness
3. Company fairness tracker → Ensure all companies get equal rotation
4. Enhanced test verification → Multi-point validation (timestamp + success count + job count)

**Impact:** Fair rotation across all sources, reliable test verification

---

### Issue #3: E2E Tests Hanging/Timing Out

**Problem:** Tests hang or timeout without clear reason. No visibility into what's happening. Hard to debug.

**Root Cause:**
- Fixed 300s timeout for all operations (doesn't account for staging slowness)
- No exponential backoff for transient issues
- No pre-flight health checks (Portainer/Firestore might not be ready)
- Timeout errors lack diagnostic information

**Solutions:**
1. Adaptive timeout with backoff → Adjust based on queue type, exponential backoff
2. Pre-flight health checks → Verify Firestore, GCP, Portainer before tests
3. Status history tracking → Reconstruct timeline for debugging
4. Enhanced error reporting → Include logs, diagnostics, Google Cloud links

**Impact:** Fewer false timeouts, faster debugging when issues occur

---

## Implementation Roadmap

### Phase 1: Deduplication (2-3 hours)
**Branch:** `feature/e2e-dedup-fixes`

Files to modify:
- `src/job_finder/storage/firestore_storage.py` - Add batch_check_exists(), normalize_url()
- `src/job_finder/queue/scraper_intake.py` - Use batch checking
- `src/job_finder/scrape_runner.py` - Use batch checking

New files:
- `src/job_finder/storage/dedup_cache.py` - Caching layer

Tests:
- `tests/test_firestore_storage.py` - Test batch checking
- Run E2E to verify no regressions

### Phase 2: Rotation (3-4 hours)
**Branch:** `feature/e2e-rotation-fixes`

Files to modify:
- `src/job_finder/scrape_runner.py` - Improve _get_next_sources_by_rotation()
- `src/job_finder/storage/job_sources_manager.py` - Add health tracking

New files:
- `src/job_finder/storage/source_health_tracker.py`
- `src/job_finder/storage/company_scrape_tracker.py`

Tests:
- `tests/e2e/scenarios/scenario_04_scrape_rotation.py` - Enhanced verification
- Run Scenario 4 multiple times to verify fairness

### Phase 3: Timeout/Reliability (2-3 hours)
**Branch:** `feature/e2e-reliability-fixes`

Files to modify:
- `tests/e2e/helpers/queue_monitor.py` - Adaptive timeout, backoff

New files:
- `tests/e2e/helpers/health_check.py` - Pre-flight checks
- `tests/e2e/helpers/status_tracker.py` - Detailed diagnostics

Tests:
- `tests/e2e/run_all_scenarios.py` - Add health checks
- Run full suite to check timeout improvements

### Phase 4: Testing & Validation (2 hours)
**Branch:** `staging` (integrate all improvements)

Activities:
- Run full E2E test suite multiple times
- Monitor Google Cloud logs
- Document results
- Update README and troubleshooting guide

---

## Key Files to Monitor

### Core Logic
- `src/job_finder/scrape_runner.py` - Main scraping orchestration
- `src/job_finder/storage/firestore_storage.py` - Job storage
- `src/job_finder/storage/job_sources_manager.py` - Source management

### E2E Tests
- `tests/e2e/run_all_scenarios.py` - Main test runner
- `tests/e2e/scenarios/scenario_*.py` - Individual scenarios
- `tests/e2e/helpers/queue_monitor.py` - Queue polling

### Configuration
- `config/config.yaml` - Main config
- `docs/E2E_TEST_IMPROVEMENT_PLAN.md` - Detailed plan
- `docs/E2E_TEST_EXECUTION_GUIDE.md` - How to run tests

---

## Testing Strategy

### Before Implementation
```bash
# Baseline E2E test run
python tests/e2e/run_all_scenarios.py --verbose 2>&1 | tee baseline_$(date +%s).log
```

### After Each Phase
```bash
# Run E2E tests to verify fix
python tests/e2e/run_all_scenarios.py --verbose

# Check for regressions
python tests/test_firestore_storage.py
python tests/test_scraper_runner.py
```

### Monitoring During Tests
```bash
# In another terminal, monitor Google Cloud logs
gcloud logging read "labels.test_run_id='e2e_test_*'" --limit 50 --format=json

# Or check Portainer dashboard:
# http://nas-ip:9000
```

---

## Success Metrics

| Metric | Baseline | Target | Verification |
|--------|----------|--------|--------------|
| Duplicate jobs | High | 0 | E2E Scenario 1 passes |
| Rotation fairness | Biased | ~Equal | Scenario 4 shows all sources scraped |
| Test timeout rate | 10-20% | <2% | Run suite 10x, count failures |
| Average dedup time | 5-10s/50 jobs | <1s/50 jobs | Profile batch_check_exists() |
| Diagnostic quality | Poor | Excellent | Timeout errors include Google Cloud link |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Break existing dedup | Low | High | Keep old function, test both paths |
| Slow down rotation | Medium | Medium | Profile performance, add timeouts |
| Test flakiness increases | Low | High | Add comprehensive health checks |
| Portainer worker crashes | Low | Medium | Implement pre-flight checks |

---

## Documentation Updates Needed

After implementation:
1. Update `README.md` with E2E test running instructions
2. Update `DEPLOYMENT.md` with staging environment notes
3. Create troubleshooting guide for E2E test issues
4. Add performance tuning recommendations
5. Document monitoring/alerting setup

---

## Related Documentation

- **Detailed Technical Plan:** `docs/E2E_TEST_IMPROVEMENT_PLAN.md`
- **How to Run Tests:** `docs/E2E_TEST_EXECUTION_GUIDE.md`
- **Queue System:** `docs/queue-system.md`
- **Deployment:** `docs/deployment.md`
- **Architecture:** `docs/architecture.md`

---

## Next Immediate Steps

1. **Review this plan** and the detailed improvement plan document
2. **Create feature branches** off `staging`
3. **Start with Phase 1** (deduplication) - lowest risk, highest impact
4. **Run baseline E2E tests** before starting (document current behavior)
5. **Implement incrementally**, testing after each change
6. **Monitor Google Cloud logs** during all test runs
7. **Create PR for each phase** with test results

---

## Questions & Clarifications

### Q: Will these changes affect production?
**A:** No. All changes are internal optimization. Job dedup, rotation, and timeouts work the same externally.

### Q: How long will tests take with improvements?
**A:** Similar to now (5-15 min total) but with fewer timeouts and better diagnostics.

### Q: Should we run tests continuously?
**A:** Recommend after each deployment to staging, plus nightly smoke tests.

### Q: What if tests still fail after improvements?
**A:** Diagnostics will be much better. Error messages will include Google Cloud links and status timelines for debugging.

---

## Contact & Questions

Review detailed plan at: `docs/E2E_TEST_IMPROVEMENT_PLAN.md`  
Questions about running tests: See `docs/E2E_TEST_EXECUTION_GUIDE.md`

**Ready to start implementation!** 🚀
