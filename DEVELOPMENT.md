# Development Workflow

This document outlines the development workflow for the Job Finder project.

## Branch Strategy

### Main Branch

- **Purpose**: Production-ready code
- **Protected**: Yes (see Branch Protection below)
- **Deployment**: Automatic Docker build and push on every commit
- **Access**: Merge only through Pull Requests

### Development Branch

- **Name**: `develop`
- **Purpose**: Integration branch for features and fixes
- **Testing**: All changes should be tested here before merging to main
- **Workflow**: Feature branches merge to `develop`, `develop` merges to `main`

### Feature Branches

- **Naming**: `feature/description`, `fix/description`, `docs/description`
- **Purpose**: Individual features, bug fixes, or documentation updates
- **Lifespan**: Short-lived, deleted after merging
- **Base**: Created from and merged back to `develop`

## Workflow Example

```bash
# 1. Start from develop
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feature/add-new-job-board

# 3. Make changes and commit
git add .
git commit -m "Add Monster.com job board scraper"

# 4. Push feature branch
git push origin feature/add-new-job-board

# 5. Create Pull Request
# - Target: develop
# - Request review
# - Ensure CI passes

# 6. After PR approval and merge
git checkout develop
git pull origin develop
git branch -d feature/add-new-job-board

# 7. When ready for production
# Create PR from develop to main
# After approval, Docker build automatically deploys
```

## Commit Messages

Follow the Conventional Commits specification:

```
<type>: <short description>

<optional body with details>

<optional footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic changes)
- `refactor`: Code restructuring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat: Add RemoteOK API integration

Implement scraper for RemoteOK API with support for:
- Tag filtering
- Remote job filtering
- Rate limiting

fix: Resolve duplicate job detection issue

The batch_check_exists method was not handling empty URL lists correctly.
Added guard clause to return empty dict for empty input.

docs: Update Docker deployment guide

Add troubleshooting section for common Portainer issues.
```

## Branch Protection Rules

### Main Branch Protection

**Required Status Checks**:
- ✅ `Build and Push Docker Image` must pass
- ⚠️ `Tests` (can fail initially, should eventually pass)

**Pull Request Requirements**:
- At least 1 approval required (for team)
- All conversations must be resolved
- Branch must be up to date with main

**Additional Protections**:
- No force pushes
- No deletion
- No direct pushes (except initial setup)

**How to Configure** (GitHub Settings → Branches → Add Rule):
1. Branch name pattern: `main`
2. ☑️ Require pull request reviews before merging
   - Required approving reviews: 1 (can be 0 for solo projects)
3. ☑️ Require status checks to pass before merging
   - ☑️ Require branches to be up to date
   - Status checks: `build-and-push` (Docker build job)
4. ☑️ Do not allow bypassing the above settings
5. ☑️ Restrict who can push to matching branches
   - Add maintainers only

**For Solo Development**:
- Can disable "require approvals" (set to 0)
- Keep status check requirements
- Useful for self-review and ensuring CI passes

## Code Review Checklist

**Before Creating PR**:
- [ ] Code follows project style (run `black src/ tests/`)
- [ ] No debug code or console.logs
- [ ] Tests added for new features
- [ ] Documentation updated (README, CLAUDE.md, etc.)
- [ ] Environment variables documented in .env.example
- [ ] No secrets committed
- [ ] Local testing completed

**Reviewing PRs**:
- [ ] Code quality and readability
- [ ] Logic correctness
- [ ] Security considerations
- [ ] Performance implications
- [ ] Test coverage
- [ ] Documentation completeness

## Local Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/job_finder --cov-report=html

# Run specific tests
pytest tests/test_filters.py -v
```

### Code Quality

```bash
# Format with black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type check with mypy (optional, may have errors)
mypy src/
```

### Testing Docker Locally

```bash
# Build image
docker build -t job-finder:dev .

# Test run
docker run --rm \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/serviceAccountKey.json \
  -v $(pwd)/credentials:/app/credentials:ro \
  job-finder:dev python run_job_search.py
```

## CI/CD Pipeline

### GitHub Actions Workflows

**1. Build and Push Docker Image** (.github/workflows/docker-build-push.yml)
- **Trigger**: Push to main, Pull Request to main
- **Platforms**: linux/amd64, linux/arm64
- **Registry**: ghcr.io (GitHub Container Registry)
- **Tags**: `latest`, `main-<sha>`, branch names
- **Cache**: GitHub Actions cache for faster builds
- **Duration**: ~5-10 minutes (multi-platform)

**2. Tests** (.github/workflows/tests.yml - if exists)
- **Trigger**: Push to any branch, Pull Requests
- **Matrix**: Python 3.9, 3.10, 3.11 on Ubuntu, macOS, Windows
- **Checks**: black formatting, flake8 linting, mypy types, pytest
- **Duration**: ~1-2 minutes

### Deployment

**Automatic Deployment**:
1. Merge PR to main
2. GitHub Actions builds Docker image
3. Image pushed to ghcr.io/jdubz/job-finder:latest
4. Watchtower (in Portainer) detects new image
5. Container auto-updates (every 5 minutes polling)
6. Zero-downtime deployment

**Manual Deployment**:
```bash
# Pull latest image
docker pull ghcr.io/jdubz/job-finder:latest

# Restart container
docker-compose down && docker-compose up -d
```

## Troubleshooting

### Tests Failing on GitHub But Passing Locally

**Black formatting**:
```bash
# Format locally
black src/ tests/

# Commit and push
git add -A
git commit -m "Format code with black"
git push
```

**MyPy type errors**:
```bash
# Check types locally
mypy src/

# Fix errors or add type: ignore comments
# For now, mypy errors don't block merges
```

### Docker Build Failing

**Check build logs**:
```bash
gh run list --workflow="Build and Push Docker Image"
gh run view <run-id> --log
```

**Common issues**:
- Missing dependencies in requirements.txt
- File not found (check Dockerfile COPY statements)
- Permission issues (check file permissions)
- Build timeout (increase timeout in workflow)

### PR Cannot Merge

**Branch not up to date**:
```bash
git checkout your-branch
git fetch origin
git merge origin/main
# Resolve conflicts if any
git push
```

**Status checks not passing**:
- Check GitHub Actions tab for failure details
- Fix issues locally and push
- May need to re-run failed workflows

## Resources

- **GitHub Actions**: https://github.com/Jdubz/job-finder/actions
- **Docker Images**: https://github.com/Jdubz/job-finder/pkgs/container/job-finder
- **Issues**: https://github.com/Jdubz/job-finder/issues
- **Pull Requests**: https://github.com/Jdubz/job-finder/pulls

## Best Practices

1. **Small, Focused PRs**: Easier to review and merge
2. **Test Before Pushing**: Run tests and formatting locally
3. **Clear Commit Messages**: Follow conventional commits
4. **Document Changes**: Update relevant docs
5. **Review Your Own PR**: Check the diff before requesting review
6. **Respond to Feedback**: Address comments promptly
7. **Keep Branches Updated**: Merge main frequently
8. **Delete Merged Branches**: Keep repository clean

## Getting Help

- Check existing issues and PRs
- Review documentation (README.md, CLAUDE.md, etc.)
- Create a new issue with details and context
- Use GitHub Discussions for questions

---

Happy coding! 🚀
