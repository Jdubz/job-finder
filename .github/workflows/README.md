# GitHub Actions Workflows# GitHub Actions Workflows



This directory contains the CI/CD workflows for the job-finder project, organized following best practices to avoid duplication and run checks appropriately.Automated CI/CD workflows for job-finder project.



## 🔄 Workflow Overview---



### 1. Code Quality (`quality.yml`)## Workflows Overview

**Triggers:** Pull requests to `main` or `staging` (Python files only)

| Workflow | Trigger | Purpose | Output |

Enforces code quality standards:|----------|---------|---------|--------|

- ✅ Code formatting (black)| **docker-build-push-staging.yml** | Push to `staging` | Build & deploy staging | `:staging` tag |

- ✅ Linting (flake8)  | **docker-build-push.yml** | Push to `main` | Build & deploy production | `:latest` tag |

- ✅ Type checking (mypy)| **tests.yml** | Push/PR to any branch | Run tests | Test results |



**Why separate?** Quality checks are fast and should run on every PR, independent of tests.---



---## Workflow Details



### 2. Tests (`tests.yml`)### 1. Build and Push Staging Docker Image

**Triggers:** 

- Pull requests to `main` or `staging`**File:** `docker-build-push-staging.yml`

- Direct pushes to `staging` (development workflow)

**Triggers:**

Validates functionality:- Push to `staging` branch

- ✅ Unit tests (pytest)- Manual workflow dispatch

- ✅ Code coverage reporting

- ✅ Coverage upload to Codecov (PRs only)**Steps:**

1. Checkout code

**Why here?** Tests validate functionality and are required before merge.2. Set up Docker Buildx

3. Login to GitHub Container Registry

---4. Build Docker image

5. Tag as `:staging` and `:staging-<sha>`

### 3. Build Staging (`docker-build-push-staging.yml`)6. Push to `ghcr.io/jdubz/job-finder:staging`

**Triggers:** Pushes to `staging` branch7. Display deployment summary



Builds and deploys staging:**Deployment:**

- 🐳 Build Docker image- Watchtower pulls `:staging` image

- 📦 Push to GHCR with `staging` tag- Auto-deploys to `job-finder-staging` container

- 🚀 Auto-deploys via Watchtower (~3 min)- Expected time: ~3 minutes



**Tags:** `staging`, `staging-<sha>`**Use when:**

- Pushing changes to staging branch

---- Testing features before production

- Daily development work

### 4. Build Production (`docker-build-push.yml`)

**Triggers:** Pushes to `main` branch---



Builds and deploys production:### 2. Build and Push Production Docker Image

- 🐳 Build Docker image

- 📦 Push to GHCR with `latest` and `production` tags**File:** `docker-build-push.yml`

- 🎯 Auto-deploys via Watchtower (~5 min)

**Triggers:**

**Tags:** `latest`, `production`, `prod-<sha>`- Push to `main` branch

- Manual workflow dispatch

---

**Steps:**

## 📋 What Runs Where?1. Checkout code

2. Set up Docker Buildx

| Check | Pre-commit | Pre-push | GitHub Actions |3. Login to GitHub Container Registry

|-------|-----------|----------|----------------|4. Build Docker image

| **Black formatting** | ✅ | ❌ | ✅ (PRs only) |5. Tag as `:latest` and various semantic versions

| **Flake8 linting** | ❌ | ❌ | ✅ (PRs only) |6. Push to `ghcr.io/jdubz/job-finder:latest`

| **Mypy type checking** | ❌ | ✅ | ✅ (PRs only) |7. Display deployment summary

| **Pytest tests** | ❌ | ✅ | ✅ (PRs + staging pushes) |

| **Docker build** | ❌ | ❌ | ✅ (main/staging only) |**Deployment:**

- Watchtower pulls `:latest` image

**Key insight:** Quality checks run in CI for PRs, pre-push hooks handle direct pushes to staging. This avoids duplicate work while maintaining quality.- Auto-deploys to `job-finder-production` container

- Expected time: ~5 minutes

---

**Use when:**

## 🌿 Development Workflow- Merging PR from `staging` to `main`

- Deploying validated features to production

### Feature Development- Hotfix deployments

```bash

# 1. Branch from staging---

git checkout staging && git pull

git checkout -b feature/my-feature### 3. Tests



# 2. Develop and commit**File:** `tests.yml`

# (pre-commit: black formatting check)

git commit -m "feat: add feature"**Triggers:**

- Push to `main`, `staging`, or `develop` branches

# 3. Push- Pull requests targeting these branches

# (pre-push: mypy + tests)

git push origin feature/my-feature**Steps:**

1. Checkout code

# 4. Create PR to staging2. Set up Python 3.12

# GitHub runs: quality.yml + tests.yml3. Install dependencies

4. Run linting (flake8)

# 5. Merge to staging5. Check code formatting (black)

# GitHub runs: tests.yml + docker-build-push-staging.yml6. Type checking (mypy)

# Auto-deploys to staging environment7. Run unit tests (pytest)

8. Upload coverage to Codecov

# 6. Test in staging, then PR to main

# GitHub runs: quality.yml + tests.yml**No Deployment:**

- Tests only, no Docker build

# 7. Merge to main- Validates code quality

# GitHub runs: docker-build-push.yml- Reports test coverage

# Auto-deploys to production

```**Use when:**

- Every push to ensure code quality

---- Pull requests for validation

- Before merging to any branch

## 🔒 Branch Protection

---

### Recommended for `main`:

- ✅ Require PR reviews (1 approval)## Docker Image Tags

- ✅ Require status checks: `quality`, `test`

- ✅ Require branches up to date### Tag Strategy

- ❌ No direct pushes

**Production (`:latest`):**

### Recommended for `staging`:```

- ✅ Require status checks: `test`ghcr.io/jdubz/job-finder:latest

- ✅ Allow direct pushes (development)ghcr.io/jdubz/job-finder:main

- ❌ PR reviews optionalghcr.io/jdubz/job-finder:sha-abc123

```

---

**Staging (`:staging`):**

## 🚀 Manual Triggers```

ghcr.io/jdubz/job-finder:staging

Both Docker workflows support manual triggering:ghcr.io/jdubz/job-finder:staging-abc123

```

```bash

# Via GitHub UI### Tag Usage

Actions → [Select workflow] → Run workflow

| Tag | Used By | Purpose |

# Via GitHub CLI|-----|---------|---------|

gh workflow run "Build and Push Staging Docker Image"| `:latest` | Production container | Latest production release |

gh workflow run "Build and Push Production Docker Image"| `:staging` | Staging container | Latest staging build |

```| `:sha-<hash>` | Manual deployment | Specific commit deployment |

| `:staging-<hash>` | Manual staging rollback | Specific staging version |

---

---

## 💾 Caching

## Workflow Execution

All workflows use caching for speed:

- **pip:** Cached by `requirements.txt` hash### Viewing Workflow Runs

- **Docker:** Layer caching via GitHub Actions cache

**GitHub UI:**

**Average speedup:** 2-3x on cache hits1. Navigate to repository

2. Click "Actions" tab

---3. Select workflow from left sidebar

4. View recent runs

## 🐛 Troubleshooting

**Deployment Summary:**

### Quality checks failedEach workflow run includes a summary with:

```bash- Docker image tag

black src/ tests/          # Fix formatting- Image digest

flake8 src/ tests/          # Check linting- Expected deployment time

mypy src/                   # Check types- Next steps for verification

```

### Manual Workflow Trigger

### Tests failed

```bash**Via GitHub UI:**

pytest                      # Run locally1. Go to Actions tab

pytest -v                   # Verbose output2. Select workflow

pytest --lf                 # Run last failed3. Click "Run workflow"

```4. Select branch

5. Click "Run workflow" button

### Docker build failed

- Check Dockerfile syntax**Via GitHub CLI:**

- Verify all files are committed```bash

- Review build logs in Actions# Trigger staging deployment

gh workflow run docker-build-push-staging.yml --ref staging

### Deployment not happening

- Check Watchtower is running: `docker ps | grep watchtower`# Trigger production deployment

- View logs: `docker logs watchtower -f`gh workflow run docker-build-push.yml --ref main

- Verify image tags match

# Trigger tests

---gh workflow run tests.yml --ref staging

```

## 📊 Usage Stats

---

**Free tier: 2,000 minutes/month**

## Monitoring Deployments

Estimated usage:

- Quality: ~100 min/month (50 PRs × 2 min)### GitHub Actions Logs

- Tests: ~450 min/month (150 runs × 3 min)

- Staging builds: ~500 min/month (100 pushes × 5 min)**View build logs:**

- Prod builds: ~50 min/month (10 pushes × 5 min)```

GitHub → Actions → Select workflow run → View logs

**Total: ~1,100 min/month** (well within limits!)```



---**Check for errors:**

- Red X: Build/test failed

## 📝 Recent Changes- Yellow circle: In progress

- Green checkmark: Success

**2025-10-19:** Workflow cleanup

- ❌ Removed non-existent `develop` branch from triggers### Container Deployment

- ❌ Removed duplicate quality checks from tests.yml

- ✅ Created separate quality.yml for linting/formatting/type checking**After workflow completes:**

- ✅ Added caching for faster runs

- ✅ Updated tags for better organization```bash

- ✅ Added path filters to skip unnecessary runs# Check staging deployment

docker logs job-finder-staging -f --tail 50

---

# Check production deployment

**Last Updated:** 2025-10-19docker logs job-finder-production -f --tail 50


# Verify image tag
docker inspect job-finder-staging | grep Image
```

---

## Troubleshooting

### Workflow Not Triggering

**Check:**
1. Branch name is correct (`staging` or `main`)
2. Changes pushed successfully: `git log origin/staging`
3. Workflow file syntax is valid
4. GitHub Actions enabled for repository

**Fix:**
```bash
# Verify push succeeded
git log origin/staging --oneline -5

# Manually trigger workflow
gh workflow run docker-build-push-staging.yml --ref staging
```

---

### Build Failing

**Common causes:**
1. Docker build errors
2. Invalid Dockerfile
3. Missing dependencies
4. Network issues

**Debug:**
1. Check workflow logs in GitHub Actions
2. Build locally to reproduce:
   ```bash
   docker build -t test-build .
   ```
3. Fix issue and push again

---

### Tests Failing

**Check:**
1. Test output in workflow logs
2. Which tests failed
3. Error messages

**Fix:**
```bash
# Run tests locally
pytest tests/ -v

# Run specific test
pytest tests/test_file.py::test_function -v

# Fix failing tests
# Commit and push
```

---

### Image Not Deploying

**Symptoms:**
- Workflow succeeds but container not updated

**Check:**
1. Watchtower is running:
   ```bash
   docker ps | grep watchtower
   ```

2. Watchtower logs:
   ```bash
   docker logs watchtower-staging
   ```

3. Image tag matches:
   ```bash
   docker inspect job-finder-staging | grep Image
   # Should be: ghcr.io/jdubz/job-finder:staging
   ```

**Fix:**
```bash
# Restart Watchtower
docker restart watchtower-staging

# Or manually pull new image
docker pull ghcr.io/jdubz/job-finder:staging
docker restart job-finder-staging
```

---

## Environment Variables & Secrets

### Required Secrets

**GitHub Repository Secrets:**
- `GITHUB_TOKEN` - Automatically provided by GitHub Actions
  - Used for: Pushing to GitHub Container Registry
  - Permissions: `packages: write`

**No additional secrets needed** - `GITHUB_TOKEN` has all required permissions.

### Environment Variables

**Set in workflow files:**
```yaml
env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
```

**Available variables:**
- `${{ github.repository }}` - Repository name (Jdubz/job-finder)
- `${{ github.actor }}` - User triggering workflow
- `${{ github.sha }}` - Commit SHA
- `${{ github.ref }}` - Branch ref

---

## Best Practices

### DO ✅

- Monitor workflow runs after pushing
- Check deployment logs after build completes
- Fix test failures immediately
- Use meaningful commit messages
- Review workflow summaries

### DON'T ❌

- Ignore failed workflows
- Skip tests
- Force push to branches with active workflows
- Modify workflows without testing
- Deploy with failing tests

---

## Workflow Modification

### Adding New Workflow

1. Create file in `.github/workflows/`
2. Define trigger (`on:`)
3. Define jobs and steps
4. Test with `act` (local GitHub Actions runner)
5. Push and verify in GitHub Actions

### Modifying Existing Workflow

1. Edit workflow file
2. Commit changes
3. Push to test branch
4. Verify workflow runs correctly
5. Merge to target branch

### Testing Workflows Locally

**Using `act`:**
```bash
# Install act
brew install act  # macOS
# or
sudo apt install act  # Linux

# Test workflow
act -W .github/workflows/docker-build-push-staging.yml

# Test specific job
act -j build-and-push-staging
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| View workflows | GitHub → Actions |
| Trigger manually | GitHub → Actions → Run workflow |
| Check logs | GitHub → Actions → Workflow run |
| View images | GitHub → Packages |
| Test locally | `act -W .github/workflows/file.yml` |
| Validate syntax | `actionlint .github/workflows/` |

---

## Related Documentation

- [BRANCHING_STRATEGY.md](../../docs/BRANCHING_STRATEGY.md) - Git workflow
- [DEPLOYMENT.md](../../DEPLOYMENT.md) - Deployment overview
- [PORTAINER_DEPLOYMENT_GUIDE.md](../../docs/PORTAINER_DEPLOYMENT_GUIDE.md) - Container deployment

---

## Support

For workflow issues:

1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Test locally with `act`
4. Verify secrets and permissions
5. Check Watchtower logs for deployment issues
