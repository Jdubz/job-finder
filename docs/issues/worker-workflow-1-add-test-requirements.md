# WORKER-WORKFLOW-1 — Add Test Requirements to Deployments

## Issue Metadata

```yaml
Title: WORKER-WORKFLOW-1 — Add Test Requirements to Deployments
Labels: [priority-p0, repository-worker, type-bugfix, status-todo, ci-cd, safety]
Assignee: TBD
Priority: P0-Critical
Estimated Effort: 30 minutes
Repository: job-finder-worker
GitHub Issue: https://github.com/Jdubz/job-finder-worker/issues/70
```

## Summary

**CRITICAL SAFETY ISSUE**: Add test job as dependency to Docker deployment workflows to prevent deploying broken code to staging or production. Currently tests run in parallel with deployments, allowing failed code to be deployed, which creates a critical risk of production outages.

## Background & Context

### Project Overview
**Application Name**: Job Finder Application  
**Technology Stack**: Python, Docker, GitHub Actions, PostgreSQL/Firebase  
**Architecture**: Containerized Python worker with automated CI/CD pipelines

### This Repository's Role
The job-finder-worker repository contains the Python application that processes job queues, performs AI-powered job matching, and integrates with job-finder-FE frontend and job-finder-BE backend services.

### Current State
The deployment workflows currently:
- ✅ **Run tests** in parallel with Docker build (`test` job)
- ✅ **Build Docker image** in parallel with tests (`build` job)
- ✅ **Deploy to staging/production** after successful build
- ❌ **No dependency** between test job and deployment job
- ❌ **Deployments can succeed** even if tests fail

### Desired State
After completion:
- Test job runs before deployment job
- Deployment only proceeds if tests pass
- Same safety guarantees as other repositories
- Broken code cannot reach production

## Technical Specifications

### Affected Files
```yaml
MODIFY:
- .github/workflows/docker-build-push-staging.yml - Add test dependency
- .github/workflows/docker-build-push.yml - Add test dependency
- .github/workflows/README.md - Update workflow documentation

CREATE:
- scripts/workflow/test-dependency.sh - Test completion verification
```

### Technology Requirements
**Languages**: YAML, Shell Script  
**Frameworks**: GitHub Actions, Docker  
**Tools**: Python 3.9+, pytest  
**Dependencies**: Existing test infrastructure

### Code Standards
**Naming Conventions**: Follow existing workflow naming patterns  
**File Organization**: Place scripts in `scripts/workflow/` directory  
**Import Style**: Use existing shell script patterns

## Implementation Details

### Step-by-Step Tasks

1. **Analyze Current Workflow Structure**
   - Review existing `docker-build-push-staging.yml` and `docker-build-push.yml`
   - Identify current job dependencies and structure
   - Document baseline deployment time

2. **Add Test Dependencies**
   - Modify staging workflow to depend on test job
   - Modify production workflow to depend on test job
   - Ensure proper job ordering and failure handling

3. **Update Workflow Documentation**
   - Update `.github/workflows/README.md`
   - Document the new test requirement
   - Add troubleshooting for test failures

4. **Verify Deployment Safety**
   - Test that deployment fails when tests fail
   - Test that deployment succeeds when tests pass
   - Document rollback procedures

### Architecture Decisions

**Why this approach:**
- Simple dependency addition to existing workflows
- Minimal changes to proven deployment process
- Consistent with safety patterns in other repositories

**Alternatives considered:**
- Custom test verification script: More complex, potential for divergence
- Skip test requirement: Unacceptable safety risk

### Dependencies & Integration

**Internal Dependencies:**
- Depends on: Existing test job in workflows
- Consumed by: Docker build and deployment jobs

**External Dependencies:**
- APIs: None (tests run in GitHub Actions environment)
- Services: Docker Hub/GitHub Container Registry

## Testing Requirements

### Test Coverage Required

**Integration Tests:**
- Workflow dependency correctly implemented
- Test failure blocks deployment
- Test success allows deployment

**Manual Testing Checklist**
- [ ] Staging deployment requires passing tests
- [ ] Production deployment requires passing tests
- [ ] Test failure prevents deployment to either environment
- [ ] Deployment time increase is minimal

### Test Data

**Sample workflow scenarios:**
- Tests pass → deployment proceeds
- Tests fail → deployment blocked
- Partial test failures → deployment blocked

## Acceptance Criteria

- [ ] Test job is dependency for staging deployment
- [ ] Test job is dependency for production deployment
- [ ] Deployment fails if tests fail
- [ ] Deployment succeeds if tests pass
- [ ] No significant increase in deployment time
- [ ] Workflow documentation updated

## Environment Setup

### Prerequisites
```bash
# Required tools and versions
GitHub Actions: configured
Docker: installed
Python: 3.9+
pytest: configured
```

### Repository Setup
```bash
# Clone worker repository
git clone https://github.com/Jdubz/job-finder-worker.git
cd job-finder-worker

# Environment variables needed
cp .env.example .env
# Configure test environment settings
```

### Running Locally
```bash
# Run tests locally (equivalent to CI)
python -m pytest

# Test workflow changes locally
# (Requires GitHub Actions configuration)
```

## Code Examples & Patterns

### Example Implementation

**Current problematic workflow:**
```yaml
jobs:
  test:
    # Runs tests
  build:
    # Builds Docker image
  deploy:
    needs: build
    # Deploys even if tests failed
```

**Fixed workflow with safety:**
```yaml
jobs:
  test:
    # Runs tests
  build:
    needs: test
    # Only builds if tests pass
  deploy:
    needs: [test, build]
    # Only deploys if tests and build pass
```

## Security & Performance Considerations

### Security
- [ ] No sensitive data exposed in workflow failures
- [ ] Proper cleanup of test artifacts

### Performance
- [ ] Test dependency adds <1 minute to deployment time
- [ ] Parallel execution where possible
- [ ] Efficient job ordering

### Error Handling
```yaml
# Example error handling in workflow
- name: Deploy to Staging
  if: success()  # Only run if previous jobs succeeded
  run: |
    echo "Deploying to staging..."
    # Deployment commands
```

## Documentation Requirements

### Code Documentation
- [ ] Add comments to workflow explaining test requirement
- [ ] Document test failure scenarios and resolution

### README Updates
Update repository README.md with:
- [ ] Deployment now requires passing tests
- [ ] Test failure blocks deployment
- [ ] How to troubleshoot test failures

## Commit Message Requirements

All commits for this issue must use **semantic commit structure**:

```
fix(workflows): add test requirements to deployment workflows

Add test job as dependency for Docker deployments to prevent
broken code from reaching staging and production environments.

Closes #70
```

### Commit Types
- `fix:` - Bug fix (deployment safety issue)

## PR Checklist

When submitting the PR for this issue:

- [ ] PR title matches issue title
- [ ] PR description references issue: `Closes #70`
- [ ] All acceptance criteria met
- [ ] All tests pass locally
- [ ] No linter errors or warnings
- [ ] Code follows project style guide
- [ ] Self-review completed

## Timeline & Milestones

**Estimated Effort**: 30 minutes  
**Target Completion**: Same day (critical safety fix)  
**Dependencies**: None  
**Blocks**: Safe deployment of worker changes

## Success Metrics

How we'll measure success:

- **Safety**: Deployments now require passing tests
- **Reliability**: No more broken code deployments
- **Consistency**: Same safety standards across all repositories
- **Speed**: Test dependency adds minimal time overhead

## Rollback Plan

If this change causes issues:

1. **Immediate rollback**:
   ```bash
   # Remove test dependency if causing workflow failures
   git revert [commit-hash]
   ```

2. **Decision criteria**: If test dependency consistently causes deployment issues

## Questions & Clarifications

**If you need clarification during implementation:**

1. **Add a comment** to this issue with what's unclear
2. **Tag the PM** for guidance
3. **Don't assume** - always ask if requirements are ambiguous

## Issue Lifecycle

```
TODO → IN PROGRESS → REVIEW → DONE
```

**Update this issue**:
- When starting work: Add `status-in-progress` label
- When PR is ready: Add `status-review` label and PR link
- When merged: Add `status-done` label and close issue

**PR must reference this issue**:
- Use `Closes #70` in PR description

---

**Created**: 2025-10-21  
**Created By**: PM  
**Priority Justification**: Critical deployment safety issue - prevents broken code from reaching production  
**Last Updated**: 2025-10-21
