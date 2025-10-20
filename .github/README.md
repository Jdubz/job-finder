# GitHub Actions Setup

This directory contains GitHub Actions workflows for CI/CD automation.

## Workflows

### `tests.yml`
- **Trigger**: Push/PR to `main` or `develop`
- **Purpose**: Run tests, type checking, and code quality checks
- **Secrets**: None required

### `docker-build-push.yml`
- **Trigger**: Push to `main`
- **Purpose**: Build and push Docker images to GHCR
- **Secrets**: None required (uses GitHub token)

## Firestore Indexes

**Note**: Firestore indexes are managed in the [job-finder-FE project](https://github.com/Jdubz/portfolio/), not in this repository.

See [FIRESTORE_INDEXES.md](../FIRESTORE_INDEXES.md) for index requirements and management details.
