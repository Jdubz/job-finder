# WORKER-CICD-1 — Set Up GitHub Actions CI/CD Pipeline

- **Status**: To Do
- **Owner**: Worker A
- **Priority**: P1 (High Impact)
- **Labels**: priority-p1, repository-worker, type-ci, ci-cd
- **Estimated Effort**: 3-4 hours
- **Dependencies**: None

## What This Issue Covers

Set up comprehensive GitHub Actions workflows for the job-finder-worker Python project to ensure code quality, automated testing, and reliable deployments. Currently, the worker has no CI/CD automation, which creates deployment risks.

## Context

The job-finder-worker is a critical component that processes job queues and integrates with:
- job-finder-BE (backend Cloud Functions)
- job-finder-FE (frontend application)
- job-finder-shared-types (shared type definitions)

Without proper CI/CD:
- Code quality issues may not be caught before deployment
- Testing is manual and inconsistent
- Deployments lack verification steps
- No automated rollback capabilities

## Tasks

### 1. Create CI Workflow (`.github/workflows/ci.yml`)
- [ ] Set up Python 3.9+ testing environment
- [ ] Install dependencies from `requirements.txt` and `requirements-test.txt`
- [ ] Run linting: `flake8 src/ tests/`
- [ ] Run type checking: `mypy src/`
- [ ] Run security checks: `bandit -r src/`
- [ ] Execute full test suite: `pytest --cov=src/job_finder`
- [ ] Generate coverage report (fail if <80% coverage)
- [ ] Test on multiple Python versions (3.9, 3.10, 3.11)

### 2. Create Docker Build Workflow (`.github/workflows/docker-build.yml`)
- [ ] Build Docker image using `Dockerfile`
- [ ] Tag with commit SHA and branch name
- [ ] Push to GitHub Container Registry
- [ ] Run container security scanning
- [ ] Test container functionality with smoke tests
- [ ] Deploy to staging environment on main branch

### 3. Create Production Deployment Workflow (`.github/workflows/deploy-production.yml`)
- [ ] Require manual approval for production deployments
- [ ] Deploy to production Docker environment
- [ ] Run integration tests against live service
- [ ] Verify service health endpoints
- [ ] Tag deployment with version and timestamp
- [ ] Create rollback plan documentation

### 4. Create Security Scanning Workflow (`.github/workflows/security.yml`)
- [ ] Run dependency vulnerability scanning
- [ ] Check for secrets in code
- [ ] Run container security scans
- [ ] Validate Docker image security
- [ ] Check for insecure configurations

### 5. Create Release Management
- [ ] Set up automated semantic versioning
- [ ] Create GitHub releases on tags
- [ ] Update deployment documentation
- [ ] Notify team of new releases

## Acceptance Criteria

- [ ] All workflows pass on main branch
- [ ] PRs require passing CI checks before merge
- [ ] Docker images are built and pushed automatically
- [ ] Production deployments require manual approval
- [ ] Security scanning runs on all code changes
- [ ] Coverage reports are generated and accessible
- [ ] Deployment rollbacks are documented and automated

## Test Commands

```bash
# Local testing (equivalent to CI)
python -m pytest --cov=src/job_finder --cov-report=html
flake8 src/ tests/
mypy src/
bandit -r src/

# Docker build test
docker build -t job-finder-worker:test .
docker run --rm job-finder-worker:test python -c "import job_finder; print('Import successful')"
```

## Useful Files

- `requirements.txt` - Production dependencies
- `requirements-test.txt` - Testing dependencies
- `Dockerfile` - Container definition
- `pyproject.toml` - Project configuration
- `pytest.ini` - Test configuration

## Dependencies

- None (can start immediately)

## Notes

- Focus on reliability and security first
- Use GitHub Container Registry for image storage
- Ensure all secrets are properly configured
- Test workflows thoroughly before enabling on main branch
- Consider adding matrix builds for multiple Python versions
