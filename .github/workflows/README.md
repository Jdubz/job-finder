# GitHub Actions Workflows

Automated CI/CD workflows for job-finder project.

---

## Workflows Overview

| Workflow | Trigger | Purpose | Output |
|----------|---------|---------|--------|
| **docker-build-push-staging.yml** | Push to `staging` | Build & deploy staging | `:staging` tag |
| **docker-build-push.yml** | Push to `main` | Build & deploy production | `:latest` tag |
| **tests.yml** | Push/PR to any branch | Run tests | Test results |

---

## Workflow Details

### 1. Build and Push Staging Docker Image

**File:** `docker-build-push-staging.yml`

**Triggers:**
- Push to `staging` branch
- Manual workflow dispatch

**Steps:**
1. Checkout code
2. Set up Docker Buildx
3. Login to GitHub Container Registry
4. Build Docker image
5. Tag as `:staging` and `:staging-<sha>`
6. Push to `ghcr.io/jdubz/job-finder:staging`
7. Display deployment summary

**Deployment:**
- Watchtower pulls `:staging` image
- Auto-deploys to `job-finder-staging` container
- Expected time: ~3 minutes

**Use when:**
- Pushing changes to staging branch
- Testing features before production
- Daily development work

---

### 2. Build and Push Production Docker Image

**File:** `docker-build-push.yml`

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

**Steps:**
1. Checkout code
2. Set up Docker Buildx
3. Login to GitHub Container Registry
4. Build Docker image
5. Tag as `:latest` and various semantic versions
6. Push to `ghcr.io/jdubz/job-finder:latest`
7. Display deployment summary

**Deployment:**
- Watchtower pulls `:latest` image
- Auto-deploys to `job-finder-production` container
- Expected time: ~5 minutes

**Use when:**
- Merging PR from `staging` to `main`
- Deploying validated features to production
- Hotfix deployments

---

### 3. Tests

**File:** `tests.yml`

**Triggers:**
- Push to `main`, `staging`, or `develop` branches
- Pull requests targeting these branches

**Steps:**
1. Checkout code
2. Set up Python 3.12
3. Install dependencies
4. Run linting (flake8)
5. Check code formatting (black)
6. Type checking (mypy)
7. Run unit tests (pytest)
8. Upload coverage to Codecov

**No Deployment:**
- Tests only, no Docker build
- Validates code quality
- Reports test coverage

**Use when:**
- Every push to ensure code quality
- Pull requests for validation
- Before merging to any branch

---

## Docker Image Tags

### Tag Strategy

**Production (`:latest`):**
```
ghcr.io/jdubz/job-finder:latest
ghcr.io/jdubz/job-finder:main
ghcr.io/jdubz/job-finder:sha-abc123
```

**Staging (`:staging`):**
```
ghcr.io/jdubz/job-finder:staging
ghcr.io/jdubz/job-finder:staging-abc123
```

### Tag Usage

| Tag | Used By | Purpose |
|-----|---------|---------|
| `:latest` | Production container | Latest production release |
| `:staging` | Staging container | Latest staging build |
| `:sha-<hash>` | Manual deployment | Specific commit deployment |
| `:staging-<hash>` | Manual staging rollback | Specific staging version |

---

## Workflow Execution

### Viewing Workflow Runs

**GitHub UI:**
1. Navigate to repository
2. Click "Actions" tab
3. Select workflow from left sidebar
4. View recent runs

**Deployment Summary:**
Each workflow run includes a summary with:
- Docker image tag
- Image digest
- Expected deployment time
- Next steps for verification

### Manual Workflow Trigger

**Via GitHub UI:**
1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Select branch
5. Click "Run workflow" button

**Via GitHub CLI:**
```bash
# Trigger staging deployment
gh workflow run docker-build-push-staging.yml --ref staging

# Trigger production deployment
gh workflow run docker-build-push.yml --ref main

# Trigger tests
gh workflow run tests.yml --ref staging
```

---

## Monitoring Deployments

### GitHub Actions Logs

**View build logs:**
```
GitHub → Actions → Select workflow run → View logs
```

**Check for errors:**
- Red X: Build/test failed
- Yellow circle: In progress
- Green checkmark: Success

### Container Deployment

**After workflow completes:**

```bash
# Check staging deployment
docker logs job-finder-staging -f --tail 50

# Check production deployment
docker logs job-finder-production -f --tail 50

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
