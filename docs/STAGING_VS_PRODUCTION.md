# Staging vs Production Environment Comparison

Complete reference for understanding the differences between staging and production deployments.

---

## Quick Reference Table

| Aspect | Staging | Production |
|--------|---------|------------|
| **Database** | `portfolio-staging` | `portfolio` |
| **Config File** | `config.yaml` | `config.production.yaml` |
| **Container Name** | `job-finder-staging` | `job-finder-production` |
| **Network** | `job-finder-staging-network` | `job-finder-production-network` |
| **CPU Limit** | 1.0 CPU | 1.5 CPU |
| **Memory Limit** | 1GB | 1.5GB |
| **Watchtower Interval** | 3 minutes | 5 minutes |
| **Log Directory** | `logs-staging/` | `logs/` |
| **Data Directory** | `data-staging/` | `data/` |
| **Purpose** | Testing, development | Live job searches |
| **Update Frequency** | Aggressive (every push) | Stable (tagged releases) |

---

## Detailed Comparison

### 1. Database Configuration

#### Staging
```yaml
environment:
  - PROFILE_DATABASE_NAME=portfolio-staging
  - STORAGE_DATABASE_NAME=portfolio-staging
```

**Uses:** `portfolio-staging` Firestore database

**Purpose:**
- Isolate test data from production
- Safe to delete/reset data
- Test database migrations
- Experiment with queue items

**Data Volume:** Lower (test data only)

#### Production
```yaml
environment:
  - PROFILE_DATABASE_NAME=portfolio
  - STORAGE_DATABASE_NAME=portfolio
```

**Uses:** `portfolio` Firestore database

**Purpose:**
- Live user data
- Actual job matches
- Real queue processing
- Production metrics

**Data Volume:** Higher (all real data)

**⚠️ CRITICAL:** Never point production to staging database or vice versa!

---

### 2. Resource Allocation

#### Staging Resources

```yaml
deploy:
  resources:
    limits:
      cpus: '1.0'
      memory: 1G
    reservations:
      cpus: '0.25'
      memory: 256M
```

**Rationale:**
- **Lower cost** - Staging doesn't need production-level resources
- **Sufficient for testing** - Can process test queue items
- **Resource-efficient** - Runs on smaller infrastructure

**Performance Expectations:**
- Slower processing than production
- May queue up during heavy testing
- Acceptable latency for testing

#### Production Resources

```yaml
deploy:
  resources:
    limits:
      cpus: '1.5'
      memory: 1.5G
    reservations:
      cpus: '0.5'
      memory: 512M
```

**Rationale:**
- **Better performance** - Faster queue processing
- **Handles load** - Can process multiple jobs simultaneously
- **Reliability** - Room for spikes without degradation

**Performance Expectations:**
- Fast queue processing
- Minimal latency
- Stable under load

---

### 3. Update Strategy

#### Staging: Aggressive Updates

```yaml
watchtower:
  environment:
    - WATCHTOWER_POLL_INTERVAL=180  # 3 minutes
```

**Git Branch:** `develop` (or feature branches)

**Update Frequency:** Every 3 minutes

**Purpose:**
- Quick feedback on code changes
- Continuous deployment for testing
- Catch issues early

**Deployment Flow:**
```
Push to develop → Build image → Deploy to staging (3min)
```

#### Production: Stable Updates

```yaml
watchtower:
  environment:
    - WATCHTOWER_POLL_INTERVAL=300  # 5 minutes
```

**Git Branch:** `main` (tagged releases only)

**Update Frequency:** Every 5 minutes (but only on tagged releases)

**Purpose:**
- Stable, tested deployments
- Controlled release schedule
- Minimize disruption

**Deployment Flow:**
```
Test in staging → Tag release → Merge to main → Deploy to production (5min)
```

---

### 4. Configuration Files

#### Staging Config

**File:** `config/config.yaml`

```yaml
profile:
  firestore:
    database_name: "portfolio-staging"

storage:
  database_name: "portfolio-staging"

ai:
  min_match_score: 70  # Lower threshold for testing
```

**Characteristics:**
- Lower match score threshold (more permissive)
- More verbose logging
- Experimental features enabled
- Test-friendly settings

#### Production Config

**File:** `config/config.production.yaml`

```yaml
profile:
  firestore:
    database_name: "portfolio"

storage:
  database_name: "portfolio"

ai:
  min_match_score: 80  # Strict threshold
```

**Characteristics:**
- Strict match score threshold (quality over quantity)
- Production logging levels
- Only stable features
- Optimized for performance

---

### 5. Directory Structure

#### Staging Directories

```
/path/to/job-finder-staging/
├── credentials/
│   └── serviceAccountKey.json
├── config/
│   └── config.yaml              # Staging config
├── logs-staging/                # Separate logs
│   ├── scheduler.log
│   └── queue_worker.log
└── data-staging/                # Separate data
    └── test_data.json
```

**Log Retention:** 7 days
**Data:** Can be deleted/reset anytime

#### Production Directories

```
/path/to/job-finder-production/
├── credentials/
│   └── serviceAccountKey.json
├── config/
│   └── config.production.yaml   # Production config
├── logs/                        # Production logs
│   ├── scheduler.log
│   └── queue_worker.log
└── data/                        # Production data
    └── production_data.json
```

**Log Retention:** 30 days
**Data:** Critical, backed up regularly

---

### 6. Network Isolation

#### Staging Network

```yaml
networks:
  job-finder-staging-network:
    driver: bridge
```

**Isolation:** Completely isolated from production

**Accessible To:**
- `job-finder-staging` container
- `watchtower-staging` container
- Other staging services (if added)

#### Production Network

```yaml
networks:
  job-finder-production-network:
    driver: bridge
```

**Isolation:** Completely isolated from staging

**Accessible To:**
- `job-finder-production` container
- `watchtower-production` container
- Other production services (if added)

**Why separate networks?**
- Security boundary
- Prevents accidental cross-environment communication
- Easier troubleshooting
- Clear environment separation

---

### 7. Monitoring & Alerting

#### Staging Monitoring

**Health Checks:** Basic

```yaml
healthcheck:
  interval: 5m
  retries: 3
```

**Alerting:** Optional

```yaml
WATCHTOWER_NOTIFICATION_URL=  # Optional
```

**Rationale:**
- Lower stakes
- Developers can check manually
- Downtime acceptable

#### Production Monitoring

**Health Checks:** Same as staging (can be enhanced)

**Alerting:** Recommended

```yaml
WATCHTOWER_NOTIFICATION_URL=discord://webhook_token@webhook_id
```

**Rationale:**
- Critical service
- Need immediate notification of issues
- Downtime impacts users

**Recommended Alerts:**
- Container restarts
- Deployment failures
- Health check failures
- Queue processing errors

---

### 8. API Keys & Credentials

#### Staging API Keys

**Anthropic API Key:**
- Can use personal/development tier
- Lower rate limits acceptable
- May share with other dev projects

**OpenAI API Key:**
- Optional, development tier
- Lower rate limits acceptable

**Purpose:**
- Cost-effective testing
- Experimentation
- Feature development

#### Production API Keys

**Anthropic API Key:**
- **MUST** use production tier
- Higher rate limits required
- Dedicated to production only

**OpenAI API Key:**
- Production tier if used
- Higher rate limits required

**Purpose:**
- Reliable service
- Handle production load
- Meet SLAs

**⚠️ IMPORTANT:** Use separate API keys for staging and production

---

### 9. Data Lifecycle

#### Staging Data

**Retention:**
- Queue items: 7 days
- Logs: 7 days
- Job matches: Can be purged anytime

**Cleanup:**
```bash
# Safe to run anytime
python scripts/cleanup_staging_db.py
```

**Purpose:**
- Testing migrations
- Experimenting with data structures
- Validating queue processing

**Volume:** ~100-500 items typical

#### Production Data

**Retention:**
- Queue items: 30 days (successful), indefinite (failed)
- Logs: 30 days
- Job matches: Permanent

**Cleanup:**
```bash
# Run with caution, production data!
python scripts/clean_old_completed.py --days 30
```

**Purpose:**
- Real user job matches
- Analytics and metrics
- Historical data

**Volume:** ~1,000-10,000 items expected

---

### 10. Testing & Validation

#### Staging Validation

**Before deploying to staging:**
- ✅ Unit tests pass
- ✅ Linting passes
- ✅ No obvious bugs

**In staging:**
- Test new features
- Validate queue processing
- Check AI matching quality
- Test database operations
- Experiment freely

**Acceptable Issues:**
- Minor bugs
- Performance issues
- UI quirks
- Experimental failures

#### Production Validation

**Before deploying to production:**
- ✅ All staging tests pass
- ✅ No errors in staging logs
- ✅ Feature validated by QA
- ✅ Performance acceptable
- ✅ Security reviewed

**In production:**
- Monitor queue stats
- Check error rates
- Verify job match quality
- Monitor resource usage

**Unacceptable Issues:**
- Data loss
- Security vulnerabilities
- Performance degradation
- Service outages

---

## Migration Between Environments

### Promoting Code: Staging → Production

```bash
# 1. Verify staging is working
docker logs job-finder-staging --tail 100

# 2. Tag release
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin v1.2.3

# 3. Merge to main
git checkout main
git merge develop
git push origin main

# 4. Wait for production auto-deploy (5min)
# Or manually in Portainer: Stacks → job-finder-production → Update

# 5. Verify production deployment
docker logs job-finder-production --tail 100
```

### Migrating Data: Staging → Production

**⚠️ CAUTION:** Only migrate tested, validated data

```bash
# Use migration scripts with care
python scripts/migrate_data.py \
  --source portfolio-staging \
  --target portfolio \
  --dry-run  # Test first!

# After verifying dry run
python scripts/migrate_data.py \
  --source portfolio-staging \
  --target portfolio
```

### Copying Configuration

```bash
# Copy staging config as base for production
cp config/config.yaml config/config.production.yaml

# Edit production-specific settings
vim config/config.production.yaml

# Key changes needed:
# - database_name: "portfolio" (not "portfolio-staging")
# - min_match_score: 80 (stricter)
# - Any production-specific overrides
```

---

## Common Scenarios

### Scenario 1: Testing New Feature

1. ✅ Develop feature locally
2. ✅ Push to `develop` branch
3. ✅ Auto-deploys to staging (3min)
4. ✅ Test in staging environment
5. ✅ Verify works as expected
6. ✅ Merge to `main`
7. ✅ Auto-deploys to production (5min)

### Scenario 2: Debugging Production Issue

1. ✅ Reproduce issue in staging
2. ✅ Fix issue in code
3. ✅ Test fix in staging
4. ✅ Deploy to production via merge to `main`
5. ✅ Verify fix in production

**DON'T:** Debug directly in production

### Scenario 3: Database Migration

1. ✅ Test migration script in staging
2. ✅ Verify data integrity
3. ✅ Backup production database
4. ✅ Run migration in production
5. ✅ Verify production data
6. ✅ Monitor for issues

### Scenario 4: Configuration Change

1. ✅ Update `config.yaml` in staging
2. ✅ Restart staging container
3. ✅ Test new configuration
4. ✅ Update `config.production.yaml`
5. ✅ Restart production container
6. ✅ Monitor behavior

---

## Safety Checklist

### Before Deploying to Staging
- [ ] Code compiles without errors
- [ ] Unit tests pass
- [ ] Linting passes
- [ ] No sensitive data in code

### Before Deploying to Production
- [ ] Staging tests complete
- [ ] No errors in staging logs (last 24h)
- [ ] Performance acceptable in staging
- [ ] Configuration reviewed
- [ ] API keys are production-tier
- [ ] Database backup exists
- [ ] Rollback plan prepared

### After Deploying to Production
- [ ] Container started successfully
- [ ] No errors in logs
- [ ] Queue processing working
- [ ] Resource usage normal
- [ ] Health checks passing

---

## Troubleshooting

### Issue: Staging and Production Behaving Differently

**Check:**
1. Database configuration (staging vs production)
2. Config file differences
3. API key tier/rate limits
4. Resource constraints
5. Environment variables

**Common Causes:**
- Different database data
- Different config settings
- Resource constraints in staging
- Different AI model configurations

### Issue: Changes Not Appearing in Staging

**Check:**
1. Git push completed: `git log origin/develop`
2. Docker image built: Check GitHub Actions
3. Watchtower running: `docker ps | grep watchtower`
4. Container updated: `docker logs watchtower-staging`

**Solution:**
```bash
# Force restart staging
docker restart job-finder-staging

# Or redeploy stack in Portainer
```

### Issue: Production Not Updating After Merge

**Check:**
1. Code merged to main: `git log origin/main`
2. Release tagged (if using tags)
3. Docker image built with main branch
4. Watchtower running

**Solution:**
```bash
# Manual update in Portainer
Stacks → job-finder-production → Update Stack
```

---

## Summary

| Use Staging For | Use Production For |
|-----------------|-------------------|
| Testing new features | Live job searches |
| Experimenting | Real user data |
| Development | Stability |
| Breaking changes | Validated code |
| Learning | Performance |
| Debugging | Reliability |

**Golden Rule:** If you're not sure, test in staging first! 🔒
