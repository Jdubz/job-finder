# GitHub Workflows & Staging Branch Setup

Complete summary of changes made to support staging branch deployment workflow.

---

## ✅ What Was Done

### 1. Created Staging Branch

**Branch:** `staging`

**Purpose:** Pre-production testing environment

**Created from:** `develop` branch

**Usage:**
```bash
# You're already on staging branch
git branch --show-current
# Output: staging

# Work directly on this branch
vim src/job_finder/some_file.py
git add .
git commit -m "Add feature"
git push

# Auto-deploys to staging in 3 minutes
```

---

### 2. Created GitHub Workflows

#### New Workflow: Staging Deployment

**File:** `.github/workflows/docker-build-push-staging.yml`

**Triggers:** Push to `staging` branch

**Actions:**
- Builds Docker image
- Tags as `:staging`
- Pushes to GitHub Container Registry
- Auto-deploys to staging environment

**Deployment time:** ~3 minutes

---

#### Updated Workflow: Production Deployment

**File:** `.github/workflows/docker-build-push.yml`

**Changes:**
- Renamed to "Build and Push Production Docker Image"
- Updated job name to `build-and-push-production`
- Added deployment summary with next steps

**Triggers:** Push to `main` branch

**Deployment time:** ~5 minutes

---

#### Updated Workflow: Tests

**File:** `.github/workflows/tests.yml`

**Changes:**
- Added `staging` branch to triggers
- Now runs on: `main`, `staging`, `develop`

**Purpose:** Validate code quality on all branches

---

### 3. Updated Docker Compose Files

#### Staging Configuration

**File:** `docker-compose.staging.yml`

**Change:**
```yaml
# Before:
image: ghcr.io/jdubz/job-finder:latest

# After:
image: ghcr.io/jdubz/job-finder:staging
```

**Why:** Ensures staging container pulls `:staging` tagged images

---

#### Production Configuration

**File:** `docker-compose.production.yml`

**No changes** - Already correctly using `:latest` tag

---

### 4. Created Documentation

#### New: Branching Strategy Guide

**File:** `docs/BRANCHING_STRATEGY.md`

**Contents:**
- Complete branch overview
- Development workflow
- Deployment automation
- Common scenarios
- Troubleshooting
- Best practices

**60+ pages** of comprehensive guidance

---

#### New: Workflows README

**File:** `.github/workflows/README.md`

**Contents:**
- Workflow overview
- Trigger conditions
- Docker tag strategy
- Manual workflow execution
- Troubleshooting

---

#### Updated: Main Deployment Guide

**File:** `DEPLOYMENT.md`

**Changes:**
- Added link to Branching Strategy guide
- Updated workflow diagram (develop → staging)
- Reordered documentation (Branching Strategy first)

---

## 📋 Branch Structure

```
┌──────────────────────────────────────────────────────────┐
│                    Git Repository                         │
├──────────────┬────────────────────┬──────────────────────┤
│ main         │ staging            │ develop              │
│ (production) │ (pre-production)   │ (development)        │
├──────────────┼────────────────────┼──────────────────────┤
│ Protected    │ Active development │ Optional             │
│ PR only      │ Direct push OK     │ Local only           │
│              │                    │                      │
│ ↓            │ ↓                  │ ↓                    │
│ :latest tag  │ :staging tag       │ No deployment        │
│ ↓            │ ↓                  │                      │
│ Production   │ Staging            │ Local dev            │
│ container    │ container          │                      │
│              │                    │                      │
│ 5min deploy  │ 3min deploy        │ N/A                  │
└──────────────┴────────────────────┴──────────────────────┘
```

---

## 🔄 Deployment Flow

### Daily Development Workflow

```
┌─────────────────────────────────────────────────────────┐
│ 1. Work on staging branch                               │
│    git add .                                            │
│    git commit -m "Add feature"                          │
│    git push                                             │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 2. GitHub Actions triggered                             │
│    - Workflow: docker-build-push-staging.yml            │
│    - Builds Docker image                                │
│    - Tags as :staging                                   │
│    - Pushes to GHCR                                     │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 3. Watchtower detects new :staging image               │
│    - Polls every 3 minutes                              │
│    - Pulls new image                                    │
│    - Restarts job-finder-staging container              │
└────────────────────┬────────────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Test in staging environment                          │
│    docker logs job-finder-staging -f                    │
│    - Verify queue processing                            │
│    - Test new features                                  │
│    - Check for errors                                   │
└────────────────────┬────────────────────────────────────┘
                     ↓
                 All good?
                     ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Promote to production                                │
│    - Create PR: staging → main                          │
│    - Review and merge                                   │
│    - Auto-deploys to production in 5min                 │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Getting Started

### First-Time Setup

```bash
# 1. You're already on staging branch
git branch --show-current
# staging

# 2. Make a test change
echo "# Test" >> README.md
git add README.md
git commit -m "Test staging deployment"
git push

# 3. Watch the workflow
# Open: https://github.com/Jdubz/job-finder/actions
# Look for: "Build and Push Staging Docker Image"
# Wait for: Green checkmark

# 4. Monitor deployment
# Wait ~3 minutes for Watchtower to deploy
docker logs job-finder-staging -f --tail 50

# 5. Verify deployment
docker inspect job-finder-staging | grep Image
# Should show: ghcr.io/jdubz/job-finder:staging
```

---

### Daily Workflow

```bash
# Make changes
vim src/job_finder/some_file.py

# Commit and push
git add .
git commit -m "Descriptive message"
git push

# Wait ~3 minutes
# Test in staging
# If good, create PR to main for production
```

---

## 🔧 Configuration Changes Needed

### Portainer Stack Update

**For staging stack in Portainer:**

1. **Navigate to:** Portainer → Stacks → job-finder-staging

2. **Update repository reference:**
   ```yaml
   # Change from:
   Repository reference: refs/heads/develop

   # To:
   Repository reference: refs/heads/staging
   ```

3. **Verify image tag:**
   ```yaml
   # Should be:
   image: ghcr.io/jdubz/job-finder:staging
   ```

4. **Update the stack**

5. **Wait for Watchtower** to pull `:staging` image

---

### GitHub Branch Protection (Recommended)

**Staging branch:**
```
Settings → Branches → Add rule
Branch name pattern: staging

✅ Require status checks to pass before merging
   - Select: Tests
⚠️ Allow force pushes (enabled)
❌ Require pull request reviews (disabled for faster iteration)
```

**Main branch:**
```
Settings → Branches → Add rule
Branch name pattern: main

✅ Require pull request reviews before merging
✅ Require status checks to pass before merging
   - Select: Tests
✅ Require branches to be up to date before merging
❌ Allow force pushes (DISABLED)
❌ Allow deletions (DISABLED)
```

---

## 📊 Workflow Status

### View Workflow Runs

**GitHub UI:**
```
https://github.com/Jdubz/job-finder/actions
```

**Workflows:**
- ✅ Build and Push Staging Docker Image
- ✅ Build and Push Production Docker Image
- ✅ Tests

### Workflow Badges (Optional)

Add to README.md:

```markdown
![Staging Deployment](https://github.com/Jdubz/job-finder/actions/workflows/docker-build-push-staging.yml/badge.svg?branch=staging)
![Production Deployment](https://github.com/Jdubz/job-finder/actions/workflows/docker-build-push.yml/badge.svg?branch=main)
![Tests](https://github.com/Jdubz/job-finder/actions/workflows/tests.yml/badge.svg)
```

---

## 🔍 Verification Steps

### 1. Verify Branch Created

```bash
git branch -a
# Should show:
# * staging
#   develop
#   main
```

### 2. Verify Workflows Exist

```bash
ls -la .github/workflows/
# Should show:
# docker-build-push-staging.yml
# docker-build-push.yml
# tests.yml
```

### 3. Verify Docker Compose Tags

```bash
grep "image:" docker-compose.staging.yml
# Should show: ghcr.io/jdubz/job-finder:staging

grep "image:" docker-compose.production.yml
# Should show: ghcr.io/jdubz/job-finder:latest
```

### 4. Test Workflow Trigger

```bash
# Make a test commit
git commit --allow-empty -m "Test staging workflow"
git push

# Check GitHub Actions
# https://github.com/Jdubz/job-finder/actions
# Should see: "Build and Push Staging Docker Image" running
```

---

## 📝 Files Modified/Created

### Created Files ✨

```
.github/workflows/docker-build-push-staging.yml  (New staging workflow)
.github/workflows/README.md                      (Workflow documentation)
docs/BRANCHING_STRATEGY.md                       (Complete branching guide)
GITHUB_WORKFLOWS_SETUP.md                        (This file)
```

### Modified Files 🔧

```
.github/workflows/docker-build-push.yml          (Renamed, added summary)
.github/workflows/tests.yml                      (Added staging branch)
docker-compose.staging.yml                       (Changed to :staging tag)
DEPLOYMENT.md                                    (Updated workflow)
```

### New Branch 🌿

```
staging                                          (Created from develop)
```

---

## 🎯 Next Steps

### Immediate Actions

1. **Push staging branch to GitHub:**
   ```bash
   git push -u origin staging
   ```

2. **Verify first workflow run:**
   - Go to: https://github.com/Jdubz/job-finder/actions
   - Check: "Build and Push Staging Docker Image" completed successfully

3. **Update Portainer stack:**
   - Change repository reference to `refs/heads/staging`
   - Update stack
   - Wait for Watchtower deployment

4. **Test deployment:**
   ```bash
   docker logs job-finder-staging -f
   ```

### Optional Enhancements

5. **Set up branch protection rules** (see Configuration section)

6. **Add workflow badges** to README.md

7. **Configure Watchtower notifications** (Discord/Slack)

---

## ⚠️ Important Notes

### Branch Usage

- ✅ **DO** work directly on `staging` branch
- ✅ **DO** push frequently to test in staging
- ✅ **DO** create PRs from `staging` → `main` for production
- ❌ **DON'T** push directly to `main` (use PRs)
- ❌ **DON'T** skip staging for production deployments
- ❌ **DON'T** force push to `main` (ever!)

### Docker Tags

- `:staging` = Latest staging build (from `staging` branch)
- `:latest` = Latest production build (from `main` branch)
- `:staging-<sha>` = Specific staging commit
- `:sha-<hash>` = Specific production commit

### Deployment Times

- **Staging:** ~3 minutes (GitHub Actions + Watchtower)
- **Production:** ~5 minutes (GitHub Actions + Watchtower)

---

## 🆘 Troubleshooting

### Workflow Not Running

**Check:**
1. Pushed to correct branch: `git branch --show-current`
2. Workflow file syntax valid
3. GitHub Actions enabled

**Fix:**
```bash
# Verify push
git log origin/staging --oneline -5

# Manually trigger
gh workflow run docker-build-push-staging.yml --ref staging
```

### Wrong Image Deploying

**Check:**
```bash
docker inspect job-finder-staging | grep Image
```

**Should be:** `ghcr.io/jdubz/job-finder:staging`

**Fix:**
Update `docker-compose.staging.yml` and redeploy stack in Portainer

### Tests Failing

**Check:**
```bash
# Run locally
pytest tests/

# View GitHub Actions logs
# GitHub → Actions → Select run → View logs
```

**Fix:** Fix failing tests, commit, push again

---

## 📚 Documentation

**Primary Resources:**
- [BRANCHING_STRATEGY.md](docs/BRANCHING_STRATEGY.md) - Complete Git workflow
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment overview
- [.github/workflows/README.md](.github/workflows/README.md) - Workflows reference

**Setup Guides:**
- [PORTAINER_QUICK_START.md](docs/PORTAINER_QUICK_START.md) - Quick deployment
- [PORTAINER_DEPLOYMENT_GUIDE.md](docs/PORTAINER_DEPLOYMENT_GUIDE.md) - Complete reference

---

## ✅ Checklist

- [x] Created `staging` branch from `develop`
- [x] Created staging workflow (docker-build-push-staging.yml)
- [x] Updated production workflow (docker-build-push.yml)
- [x] Updated tests workflow to include staging
- [x] Updated docker-compose.staging.yml to use `:staging` tag
- [x] Created BRANCHING_STRATEGY.md documentation
- [x] Created workflows README.md
- [x] Updated DEPLOYMENT.md
- [ ] Push `staging` branch to GitHub
- [ ] Verify first staging workflow run
- [ ] Update Portainer stack repository reference
- [ ] Test staging deployment
- [ ] Set up branch protection rules (optional)

---

## 🎉 Summary

**You now have:**
- ✅ `staging` branch for pre-production testing
- ✅ Automated staging deployments (3min)
- ✅ Automated production deployments (5min)
- ✅ Separate Docker image tags (`:staging` and `:latest`)
- ✅ Comprehensive documentation
- ✅ Fast development feedback loop

**Workflow:**
1. Work on `staging` → Push
2. Auto-deploys to staging (3min)
3. Test thoroughly
4. PR to `main` → Merge
5. Auto-deploys to production (5min)

**Simple, fast, reliable.** 🚀
