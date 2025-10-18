# Branching Strategy & Deployment Workflow

Complete guide to the job-finder branching strategy and automated deployments.

---

## Branch Overview

```
┌──────────────┬───────────────────┬──────────────────┬────────────────────┐
│ Branch       │ Purpose           │ Deploys To       │ Docker Tag         │
├──────────────┼───────────────────┼──────────────────┼────────────────────┤
│ main         │ Production        │ job-finder-      │ :latest            │
│              │ Stable releases   │ production       │                    │
│              │                   │                  │                    │
│ staging      │ Pre-production    │ job-finder-      │ :staging           │
│              │ Testing           │ staging          │                    │
│              │                   │                  │                    │
│ develop      │ Development       │ (local only)     │ N/A                │
│              │ Feature branches  │                  │                    │
└──────────────┴───────────────────┴──────────────────┴────────────────────┘
```

---

## Branch Purposes

### `main` - Production Branch

**Purpose:** Production-ready code only

**Deploys to:**
- Container: `job-finder-production`
- Database: `portfolio`
- Image: `ghcr.io/jdubz/job-finder:latest`

**Workflow:**
```yaml
# .github/workflows/docker-build-push.yml
on:
  push:
    branches: [main]
```

**Deployment:**
- Automatic on push to `main`
- Builds Docker image with `:latest` tag
- Watchtower deploys to production in ~5 minutes

**Protection Rules:**
- ✅ Require pull request reviews
- ✅ Require status checks (tests must pass)
- ✅ Require branch up to date before merge
- ✅ No force pushes
- ✅ No deletions

**Who can push:** Maintainers only (via PR from `staging`)

---

### `staging` - Pre-Production Branch

**Purpose:** Testing and validation before production

**Deploys to:**
- Container: `job-finder-staging`
- Database: `portfolio-staging`
- Image: `ghcr.io/jdubz/job-finder:staging`

**Workflow:**
```yaml
# .github/workflows/docker-build-push-staging.yml
on:
  push:
    branches: [staging]
```

**Deployment:**
- Automatic on push to `staging`
- Builds Docker image with `:staging` tag
- Watchtower deploys to staging in ~3 minutes

**Protection Rules:**
- ✅ Require status checks (tests must pass)
- ⚠️ Allow force pushes (for rebasing/cleanup)
- ⚠️ Allow direct pushes (developers work here)

**Who can push:** All developers

---

### `develop` - Development Branch

**Purpose:** Feature development and experimentation

**Deploys to:** Local development only (no automatic deployment)

**Workflow:**
```yaml
# .github/workflows/tests.yml (runs tests only)
on:
  push:
    branches: [develop]
```

**No Deployment:**
- Tests run on push
- No Docker image built
- No automatic deployment
- Local development only

**Protection Rules:**
- ✅ Require status checks (tests must pass)
- ⚠️ Allow force pushes
- ⚠️ Allow direct pushes

**Who can push:** All developers

---

## Development Workflow

### Daily Development (Feature Work)

```
1. Work on `staging` branch directly
   └─ Push to staging
      └─ Auto-builds :staging image
         └─ Auto-deploys to staging environment (3 min)
            └─ Test in staging
               ├─ ✅ Tests pass → Continue
               └─ ❌ Tests fail → Fix and push again

2. When ready for production
   └─ Create PR: staging → main
      └─ Review code
         └─ Merge to main
            └─ Auto-builds :latest image
               └─ Auto-deploys to production (5 min)
                  └─ Verify in production
```

**Key Points:**
- Work directly on `staging` branch
- Push changes immediately to test in staging environment
- Fast feedback loop (3 min deployment)
- Promote to production via PR when validated

---

### Feature Branch Workflow (Optional)

For larger features that need isolation:

```
1. Create feature branch from `staging`
   git checkout staging
   git pull
   git checkout -b feature/my-feature

2. Develop feature
   git add .
   git commit -m "Add feature"
   git push origin feature/my-feature

3. Create PR: feature/my-feature → staging
   └─ Review
      └─ Merge to staging
         └─ Auto-deploys to staging (3 min)

4. Test in staging
   └─ ✅ Validated → Create PR: staging → main
   └─ ❌ Issues → Fix in staging
```

**Use when:**
- Feature is large/complex
- Multiple developers working on same area
- Want code review before staging deployment
- Breaking changes need isolation

---

### Hotfix Workflow (Production Issues)

**For critical production bugs:**

```
1. Create hotfix branch from `main`
   git checkout main
   git pull
   git checkout -b hotfix/critical-bug

2. Fix bug
   git add .
   git commit -m "Fix critical bug"

3. Test locally
   pytest tests/

4. Create PR: hotfix → main
   └─ Emergency review
      └─ Merge to main
         └─ Auto-deploys to production (5 min)

5. Backport to staging
   git checkout staging
   git merge main
   git push
```

**Use when:**
- Production is broken
- Customer-facing issue
- Data integrity problem
- Security vulnerability

---

## Deployment Automation

### GitHub Actions Workflows

#### Production Deployment

**Workflow:** `.github/workflows/docker-build-push.yml`

```yaml
name: Build and Push Production Docker Image
on:
  push:
    branches: [main]
```

**Steps:**
1. Checkout code
2. Build Docker image
3. Tag as `:latest`
4. Push to GHCR
5. Watchtower pulls `:latest`
6. Deploys to `job-finder-production`

**Timing:** ~5 minutes from push to deployment

---

#### Staging Deployment

**Workflow:** `.github/workflows/docker-build-push-staging.yml`

```yaml
name: Build and Push Staging Docker Image
on:
  push:
    branches: [staging]
```

**Steps:**
1. Checkout code
2. Build Docker image
3. Tag as `:staging`
4. Push to GHCR
5. Watchtower pulls `:staging`
6. Deploys to `job-finder-staging`

**Timing:** ~3 minutes from push to deployment

---

#### Tests

**Workflow:** `.github/workflows/tests.yml`

```yaml
name: Tests
on:
  push:
    branches: [main, staging, develop]
  pull_request:
    branches: [main, staging, develop]
```

**Runs:**
- Linting (flake8)
- Code formatting (black)
- Type checking (mypy)
- Unit tests (pytest)
- Coverage reports

---

## Docker Image Tags

### Image Naming

**Repository:** `ghcr.io/jdubz/job-finder`

**Tags:**
```
:latest         ← Production (from main branch)
:staging        ← Staging (from staging branch)
:sha-abc123     ← Specific commit (all branches)
:staging-abc123 ← Staging commit (staging branch)
```

### Watchtower Configuration

**Staging:**
```yaml
# docker-compose.staging.yml
services:
  job-finder-staging:
    image: ghcr.io/jdubz/job-finder:staging

  watchtower-staging:
    environment:
      - WATCHTOWER_POLL_INTERVAL=180  # 3 minutes
```

**Production:**
```yaml
# docker-compose.production.yml
services:
  job-finder-production:
    image: ghcr.io/jdubz/job-finder:latest

  watchtower-production:
    environment:
      - WATCHTOWER_POLL_INTERVAL=300  # 5 minutes
```

---

## Common Scenarios

### Scenario 1: Regular Feature Development

```bash
# 1. Pull latest staging
git checkout staging
git pull

# 2. Make changes
vim src/job_finder/some_file.py

# 3. Commit and push
git add .
git commit -m "Add new feature"
git push

# 4. Wait for deployment (3 min)
# Watch logs: docker logs job-finder-staging -f

# 5. Test in staging
# Run diagnostics, test queue, etc.

# 6. If good, promote to production
# Create PR: staging → main
# Merge PR
# Wait for production deployment (5 min)
```

---

### Scenario 2: Quick Bug Fix in Staging

```bash
# Already on staging branch
vim src/job_finder/buggy_file.py

git add .
git commit -m "Fix bug in job processing"
git push

# Auto-deploys in 3 minutes
# Test immediately in staging
```

---

### Scenario 3: Rolling Back Staging

```bash
# If staging deployment breaks, rollback to previous commit
git checkout staging
git log --oneline  # Find last good commit

git reset --hard abc123  # Last good commit
git push --force

# Previous version redeploys in 3 minutes
```

---

### Scenario 4: Emergency Production Hotfix

```bash
# 1. Create hotfix from main
git checkout main
git pull
git checkout -b hotfix/critical-issue

# 2. Fix issue
vim src/job_finder/critical_file.py
git add .
git commit -m "Fix critical production issue"

# 3. Test locally
pytest tests/

# 4. Push and create PR
git push origin hotfix/critical-issue
# Create PR: hotfix → main in GitHub UI

# 5. Emergency review and merge
# Auto-deploys to production in 5 minutes

# 6. Backport to staging
git checkout staging
git merge main
git push
```

---

## Branch Protection Rules

### Recommended GitHub Settings

**Main Branch:**
```
✅ Require pull request reviews before merging
✅ Require status checks to pass before merging
   - Tests
✅ Require branches to be up to date before merging
✅ Require conversation resolution before merging
❌ Allow force pushes (disabled)
❌ Allow deletions (disabled)
```

**Staging Branch:**
```
✅ Require status checks to pass before merging
   - Tests
⚠️ Allow force pushes (enabled - for cleanup)
⚠️ Allow direct pushes (enabled - for development)
❌ Require pull request reviews (disabled - faster iteration)
```

**Develop Branch:**
```
✅ Require status checks to pass before merging
   - Tests
⚠️ Allow force pushes (enabled)
⚠️ Allow direct pushes (enabled)
❌ Require pull request reviews (disabled)
```

---

## Monitoring Deployments

### GitHub Actions

**View workflow runs:**
```
GitHub → Actions tab
├── Build and Push Production Docker Image
├── Build and Push Staging Docker Image
└── Tests
```

**Deployment summaries:**
Each workflow run shows deployment info in the summary:
- Image tag
- Digest
- Expected deployment time
- Next steps

### Docker Containers

**Check staging deployment:**
```bash
docker logs job-finder-staging -f --tail 50
```

**Check production deployment:**
```bash
docker logs job-finder-production -f --tail 50
```

**Verify correct image:**
```bash
# Staging should show :staging tag
docker inspect job-finder-staging | grep Image

# Production should show :latest tag
docker inspect job-finder-production | grep Image
```

---

## Best Practices

### DO ✅

- Work directly on `staging` branch for daily development
- Push frequently to test in staging environment
- Create PR from `staging` → `main` for production deployments
- Test thoroughly in staging before promoting to production
- Use feature branches for large, complex features
- Write clear commit messages
- Run tests locally before pushing
- Monitor deployment logs after pushing
- Use hotfix branches for production emergencies

### DON'T ❌

- Push directly to `main` (use PRs)
- Skip staging and deploy directly to production
- Force push to `main` (ever!)
- Merge untested code to `staging`
- Create long-lived feature branches
- Commit broken code
- Ignore test failures
- Deploy without monitoring logs
- Use `staging` database for production data

---

## Troubleshooting

### Deployment Not Triggering

**Check:**
1. GitHub Actions workflow ran: `GitHub → Actions`
2. Workflow succeeded (green checkmark)
3. Docker image was pushed: `GitHub → Packages`
4. Watchtower is running: `docker ps | grep watchtower`
5. Watchtower logs: `docker logs watchtower-staging`

**Fix:**
```bash
# Manually trigger workflow
# GitHub → Actions → Select workflow → Run workflow

# Or force Watchtower update
docker restart watchtower-staging
```

---

### Wrong Image Deployed

**Symptoms:**
- Code changes not appearing
- Old version running

**Check:**
```bash
# What tag is container using?
docker inspect job-finder-staging | grep Image

# Should be:
# Staging: ghcr.io/jdubz/job-finder:staging
# Production: ghcr.io/jdubz/job-finder:latest
```

**Fix:**
```bash
# Update docker-compose.yml
# Staging should use :staging
# Production should use :latest

# Redeploy stack in Portainer
```

---

### Tests Failing on Push

**Check:**
```bash
# Run tests locally
pytest tests/

# Check specific failure
pytest tests/test_specific.py -v
```

**Fix:**
1. Fix failing tests
2. Commit fix
3. Push again
4. Verify tests pass in GitHub Actions

---

## Migration Guide

### Switching from `develop` to `staging`

If you were previously using `develop` branch for deployments:

```bash
# 1. Create staging from current develop
git checkout develop
git pull
git checkout -b staging
git push -u origin staging

# 2. Update local workflow
git checkout staging  # Work here now instead of develop

# 3. Update Portainer stacks
# Change repository reference from 'develop' to 'staging'

# 4. Update docker-compose.staging.yml
# Change image tag from :latest to :staging

# 5. Push to trigger first staging deployment
git commit --allow-empty -m "Initialize staging deployment"
git push
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Switch to staging | `git checkout staging` |
| Pull latest | `git pull` |
| Push changes | `git push` |
| Create PR for production | GitHub UI: staging → main |
| Create feature branch | `git checkout -b feature/name` |
| Create hotfix | `git checkout -b hotfix/name` |
| Check deployment | `docker logs job-finder-staging -f` |
| Force redeploy | `docker restart watchtower-staging` |
| View workflows | GitHub → Actions |
| Check image tag | `docker inspect job-finder-staging \| grep Image` |

---

## Summary

**For daily work:**
1. Work on `staging` branch
2. Push changes
3. Auto-deploys to staging in 3 minutes
4. Test thoroughly
5. Create PR to `main` when ready
6. Auto-deploys to production in 5 minutes

**Simple, fast, safe.** 🚀
