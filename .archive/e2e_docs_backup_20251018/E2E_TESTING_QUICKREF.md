# E2E Testing Quick Reference

## Commands

### Fast Decision Tree Test (90-120s)
```bash
make test-e2e
```
**Tests:** Loop prevention, decision tree logic, pipeline spawning  
**Exit:** When queue empty + validation passed

### Full Quality Assessment (variable, monitors until complete)
```bash
make test-e2e-full
```
**Tests:** All production data, quality metrics, system performance  
**Exit:** When queue empty + quality report generated

## What Each Test Does

### `make test-e2e` (Fast)
1. ✅ Submit 1 test job with unique URL
2. ✅ Monitor queue until empty (3-minute timeout)
3. ✅ Validate loop prevention:
   - tracking_id on all items
   - ancestry_chain valid (no circular refs)
   - spawn_depth within limits
   - No infinite loops

**Duration:** 90-120 seconds  
**Purpose:** Validate implementation works correctly

### `make test-e2e-full` (Comprehensive)
1. ✅ Seed staging with ALL production data
2. ✅ Clean staging collections (with backup)
3. ✅ Submit all jobs to queue
4. ✅ Monitor with streaming logs until complete
5. ✅ Generate quality report

**Duration:** Variable (1-hour timeout)  
**Purpose:** Data quality assessment

## Key Features

### Both Tests
- ✅ Safe (staging-only by default)
- ✅ Automatic exit conditions
- ✅ Production database blocker
- ✅ Comprehensive validation

### Queue Monitor
- Polls every 5 seconds
- Exits when queue empty
- Shows status counts in real-time
- Optional log streaming

### Decision Tree Validation
- Checks tracking_id presence
- Validates ancestry_chain
- Verifies spawn_depth
- Detects infinite loops

## Output Locations

```
test_results/{run_id}/
├── backup/                        # Firestore backups
├── production_snapshot/           # Production data (full test only)
├── staging_backup_before/         # Staging backup (full test only)
├── monitor.log                    # Queue monitoring logs
├── decision_tree_validation.json  # Validation results (fast test)
├── test_results.json              # Complete results
└── quality_report.html            # Quality report (full test only)
```

## Troubleshooting

### Test hangs
```bash
# Check queue status
firebase firestore:collections:count job-queue --database portfolio-staging
```

### Validation fails
```bash
# View validation results
cat test_results/e2e_quick_*/decision_tree_validation.json
```

### Clear queue manually
```python
db = FirestoreClient.get_client('portfolio-staging')
for doc in db.collection('job-queue').stream():
    doc.reference.delete()
```

## Next Steps After Successful Tests

1. ✅ Phase 1 complete (loop prevention)
2. 🚧 Phase 2: State-driven processing (remove sub_task)
3. 🚧 Phase 3: Company discovery (auto-spawn companies)
4. 🚧 Phase 4: Monitoring & alerts

## Test Modes

| Mode | Duration | Data | Purpose | Exit Condition |
|------|----------|------|---------|----------------|
| Fast | 90-120s | 1 job | Validate logic | Queue empty |
| Full | Variable | All prod | Quality check | Queue empty + report |

## Important Notes

- Both tests run on **portfolio-staging** (not production)
- Tests use unique timestamped URLs to avoid duplicates
- Queue monitor has timeout (3min fast, 1hr full)
- Production database blocked by default (requires --allow-production flag)

---

**See E2E_TESTING_STRATEGY.md for complete documentation**
