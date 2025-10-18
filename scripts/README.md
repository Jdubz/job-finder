# Scripts Directory

Utility scripts for managing job-finder deployment, diagnostics, and maintenance.

---

## Deployment & Diagnostics

### `setup_production_queue.py`
Initialize the `job-queue` collection in Firestore.

**Usage:**
```bash
# Initialize production queue
python scripts/setup_production_queue.py

# Initialize staging queue
python scripts/setup_production_queue.py --database portfolio-staging

# Initialize without cleanup (leave test item)
python scripts/setup_production_queue.py --no-cleanup
```

**Purpose:**
- Creates job-queue collection if it doesn't exist
- Verifies Firestore connectivity
- Tests queue item creation

**When to use:**
- First-time deployment
- After database reset
- Troubleshooting queue issues

---

### `diagnose_production_queue.py`
Diagnose queue configuration and verify database connectivity.

**Usage:**
```bash
# Diagnose production
python scripts/diagnose_production_queue.py

# Diagnose staging
python scripts/diagnose_production_queue.py --database portfolio-staging
```

**Output:**
- ✅ Credentials verification
- ✅ Database connection status
- ✅ Queue collection status
- ✅ Recent queue items (last 7 days)
- ✅ Queue statistics

**When to use:**
- After deployment
- Troubleshooting queue issues
- Verifying database configuration
- Checking queue item creation

---

## Queue Workers

### `workers/queue_worker.py`
Main queue processing worker (runs in Docker container).

**Usage:**
```bash
# Run worker (used in Docker container)
python scripts/workers/queue_worker.py

# Configure via environment variables:
# - PROFILE_DATABASE_NAME
# - STORAGE_DATABASE_NAME
# - CONFIG_PATH
```

**Purpose:**
- Polls job-queue collection every 60 seconds
- Processes pending queue items in FIFO order
- Handles all queue item types (job, company, source discovery)

**Runs automatically in:**
- `job-finder-staging` container
- `job-finder-production` container

---

## Testing Scripts

### `test_full_pipeline.py`
Test complete granular pipeline (scrape → filter → analyze → save).

**Usage:**
```bash
python scripts/test_full_pipeline.py
```

**Purpose:**
- End-to-end pipeline testing
- Verify all 4 pipeline steps work
- Test in staging before production

---

### `testing/test_e2e_queue.py`
End-to-end queue system tests.

**Usage:**
```bash
python scripts/testing/test_e2e_queue.py
```

**Purpose:**
- Test queue submission
- Verify queue processing
- Test error handling
- Validate data integrity

---

### `test_models.py`
Tests which Claude AI models are available with your API key.

**Usage:**
```bash
python scripts/test_models.py
```

**Purpose:**
- Verify API key works
- Check model availability
- Test AI provider connection

---

### `test_pipeline.py`
Tests the complete job search pipeline end-to-end.

**Usage:**
```bash
python scripts/test_pipeline.py
```

**Purpose:**
- Full integration test
- Verify all components work together
- Debug pipeline issues

---

## Database Management

### `cleanup_staging_db.py`
Clean up staging database (safe to run anytime).

**Usage:**
```bash
python scripts/cleanup_staging_db.py

# Dry run (preview what would be deleted)
python scripts/cleanup_staging_db.py --dry-run
```

**Purpose:**
- Delete test data from staging
- Reset staging environment
- Prepare for fresh testing

**Safe for:** Staging only
**⚠️ WARNING:** Do not run on production database

---

### `migrate_production_data.py`
Migrate data between databases.

**Usage:**
```bash
# Dry run (preview migration)
python scripts/migrate_production_data.py \
  --source portfolio-staging \
  --target portfolio \
  --dry-run

# Actual migration
python scripts/migrate_production_data.py \
  --source portfolio-staging \
  --target portfolio
```

**Purpose:**
- Migrate validated data from staging to production
- Copy test data for production validation
- Backup/restore operations

**⚠️ CAUTION:** Review dry-run output before actual migration

---

## Debug Scripts

### `debug_firestore.py`
Inspects Firestore data structure and displays sample experience entries and blurbs.

**Usage:**
```bash
python scripts/debug_firestore.py
```

**Purpose:**
- Verify Firestore connection
- Inspect profile data structure
- Debug profile loading issues

---

### `debug_firestore_raw.py`
Displays raw Firestore document data without parsing.

**Usage:**
```bash
python scripts/debug_firestore_raw.py
```

**Purpose:**
- View raw Firestore documents
- Debug data format issues
- Inspect field names and types

---

## Configuration & Setup

### `setup_firestore_config.py`
Set up initial Firestore configuration documents.

**Usage:**
```bash
python scripts/setup_firestore_config.py
```

**Creates:**
- `job-finder-config/settings` document
- AI settings
- Queue settings
- Default configuration

**When to use:**
- First-time deployment
- After database reset
- Configuration cleanup

---

### `verify_production.py`
Verify production deployment is working correctly.

**Usage:**
```bash
python scripts/verify_production.py
```

**Checks:**
- Container running
- Database connectivity
- Queue processing
- Configuration validity
- API keys set

**Run after:**
- New deployment
- Configuration changes
- Troubleshooting issues

---

## Data Migration Scripts (Historical)

### `migrate_to_granular_pipeline.py`
Migrate from monolithic to granular pipeline (one-time migration).

**Status:** ✅ Completed (for historical reference)

---

### `migrate_listings_to_sources.py`
Migrate job listings to job sources configuration.

**Status:** ✅ Completed (for historical reference)

---

## Company & Source Management

### `add_phase1_companies.py`
Add initial batch of companies to database.

**Usage:**
```bash
# Add to staging
python scripts/add_phase1_companies.py --database portfolio-staging

# Add to production
python scripts/add_phase1_companies.py --database portfolio
```

**Purpose:**
- Seed database with companies
- Bulk company import
- Initial data population

---

## Running Scripts in Docker Containers

### From Host Machine

```bash
# Run diagnostic in staging container
docker exec -it job-finder-staging \
  python scripts/diagnose_production_queue.py --database portfolio-staging

# Run diagnostic in production container
docker exec -it job-finder-production \
  python scripts/diagnose_production_queue.py --database portfolio

# Setup queue in staging
docker exec -it job-finder-staging \
  python scripts/setup_production_queue.py --database portfolio-staging
```

### Inside Container

```bash
# Enter container
docker exec -it job-finder-staging bash

# Run scripts
python scripts/diagnose_production_queue.py --database portfolio-staging
python scripts/setup_production_queue.py --database portfolio-staging
```

---

## Script Dependencies

All scripts require:
- Python 3.12+
- Virtual environment activated (local) or container environment (Docker)
- Firebase credentials (`GOOGLE_APPLICATION_CREDENTIALS`)
- Appropriate database access

**Local setup:**
```bash
source venv/bin/activate
export GOOGLE_APPLICATION_CREDENTIALS=.firebase/serviceAccountKey.json
```

**Docker setup:**
Environment variables set in `docker-compose.yml`

---

## Common Patterns

### Database Selection

Most scripts accept `--database` argument:
```bash
--database portfolio-staging  # Staging
--database portfolio          # Production
```

### Dry Run Mode

Migration scripts support `--dry-run`:
```bash
python script.py --dry-run  # Preview without changes
python script.py            # Execute changes
```

### Logging

Scripts use Python logging:
- `INFO`: Normal operations
- `WARNING`: Issues to investigate
- `ERROR`: Failures requiring action

View logs:
```bash
# Script output to console
python scripts/script.py

# Container logs
docker logs job-finder-staging --tail 100
```

---

## Troubleshooting Scripts

If scripts fail:

1. **Check credentials:**
   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ls -l $GOOGLE_APPLICATION_CREDENTIALS
   ```

2. **Verify database access:**
   ```bash
   python scripts/diagnose_production_queue.py --database [db-name]
   ```

3. **Check Python environment:**
   ```bash
   which python
   python --version
   pip list | grep firebase
   ```

4. **View detailed errors:**
   ```bash
   python scripts/script.py 2>&1 | tee error.log
   ```

---

## Adding New Scripts

When creating new scripts:

1. **Add to this README** with:
   - Purpose
   - Usage examples
   - When to use

2. **Include proper logging:**
   ```python
   import logging
   logger = logging.getLogger(__name__)
   ```

3. **Support database selection:**
   ```python
   parser.add_argument('--database', default='portfolio-staging')
   ```

4. **Add dry-run mode** (for destructive operations):
   ```python
   parser.add_argument('--dry-run', action='store_true')
   ```

5. **Make executable:**
   ```bash
   chmod +x scripts/new_script.py
   ```

6. **Add shebang:**
   ```python
   #!/usr/bin/env python3
   ```

---

## Quick Reference

| Task | Script | Database |
|------|--------|----------|
| Initialize queue | `setup_production_queue.py` | Both |
| Verify deployment | `diagnose_production_queue.py` | Both |
| Clean test data | `cleanup_staging_db.py` | Staging only |
| Migrate data | `migrate_production_data.py` | Both |
| Verify production | `verify_production.py` | Production |
| Process queue | `workers/queue_worker.py` | Both (auto) |
| Test AI models | `test_models.py` | Local |
| Debug Firestore | `debug_firestore.py` | Both |

---

## Support

For script issues:

1. Check script help: `python scripts/script.py --help`
2. Review logs: `docker logs [container-name]`
3. Run diagnostics: `python scripts/diagnose_production_queue.py`
4. See main docs: `../docs/PORTAINER_DEPLOYMENT_GUIDE.md`
