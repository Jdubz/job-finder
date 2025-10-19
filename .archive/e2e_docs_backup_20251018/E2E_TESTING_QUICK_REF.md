# E2E Testing Quick Reference

## Single Command for Complete Testing

```bash
make test-e2e-full
```

This single command:
- ✅ Backs up existing Firestore data
- ✅ Cleans test collections  
- ✅ Periodically submits test jobs
- ✅ Monitors job processing with streaming logs
- ✅ Analyzes results and data quality
- ✅ Saves comprehensive reports

## What Happens

| Phase | Command | Time | Output |
|-------|---------|------|--------|
| 1. Data Backup & Clean | `data_collector.py` | 1-2 min | `test_results/{ID}/backup/` |
| 2. Run E2E Tests | `run_with_streaming.py` | 2-4 min | `test_results/{ID}/e2e_output.log` |
| 3. Analyze Results | `results_analyzer.py` | 30-60 sec | `test_results/{ID}/analysis/` |
| 4. Save Reports | Python | 10 sec | `test_results/{ID}/` |
| **Total** | | **5-10 min** | **Complete report** |

## Results Location

After running, find results in:

```
test_results/e2e_1729276448/
├── backup/                    # Firestore backups
├── e2e_output.log            # Test execution logs
├── analysis/                 # Quality metrics
└── final_report.json         # Summary
```

## Quick Examples

### Run complete suite
```bash
make test-e2e-full
```

### Run quick E2E only (2 min)
```bash
make test-e2e
```

### View latest results
```bash
ls -lrth test_results/ | tail -1  # Latest run
cat test_results/e2e_TIMESTAMP/analysis/quality_report.json
```

### With Google Cloud Logs
```bash
export GCP_PROJECT_ID=your-project-id
make test-e2e-full
```

### Scheduled testing (cron)
```bash
# Every night at 2 AM
0 2 * * * cd /path/to/job-finder && make test-e2e-full > test_results/cron.log 2>&1
```

## Key Metrics Tracked

- **Deduplication**: < 2ms per job ✓
- **Source Rotation**: > 95% fairness ✓
- **Timeouts**: < 5% occurrence ✓
- **Data Quality**: > 95% score
- **Job Success**: > 98% rate

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Command not found | `cd /path/to/job-finder && make test-e2e-full` |
| Permission denied | `make setup` to install venv |
| GCP logs not working | Set `GCP_PROJECT_ID` env var |
| Firestore timeout | Check database connectivity |
| Results not saved | Check `test_results/` directory permissions |

## Next Steps

- Full guide: `docs/E2E_TESTING_MAKEFILE.md`
- E2E architecture: `docs/E2E_COMPLETE_INTEGRATION.md`
- Data quality: `docs/DATA_QUALITY_MONITORING.md`
- All make commands: `make help`
