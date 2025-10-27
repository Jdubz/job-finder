# Documentation Index

**Job Finder Worker - Flask Application**

Welcome! This index helps you find the right documentation for your needs.

## 🚀 Getting Started

**New to the project?** Start here:

1. **[README.md](README.md)** - Project overview and basic setup
2. **[LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md)** - Complete development guide
3. **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - One-page quick reference

## 📚 Documentation by Purpose

### For First-Time Setup

- [README.md](README.md) - Features, requirements, installation
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md#initial-setup) - Detailed setup steps
- [.env.example](.env.example) - Environment variable template

### For Development

- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) - Complete development guide
- [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Quick command reference
- [Makefile](Makefile) - Available make commands

### For Deployment

- [FLASK_DEPLOYMENT.md](FLASK_DEPLOYMENT.md) - Complete deployment guide
- [FLASK_DEPLOYMENT.md#process-management](FLASK_DEPLOYMENT.md#process-management) - systemd, supervisor, PM2 setup
- [FLASK_DEPLOYMENT.md#monitoring](FLASK_DEPLOYMENT.md#monitoring) - Health checks and monitoring

### For Testing

- [TEST_IMPROVEMENTS_FINAL_REPORT.md](TEST_IMPROVEMENTS_FINAL_REPORT.md) - Test coverage report
- [LOCAL_DEVELOPMENT.md#running-tests](LOCAL_DEVELOPMENT.md#running-tests) - How to run tests
- [tests/](tests/) - Test files

### For Migration from Docker

- [FLASK_MIGRATION_SUMMARY.md](FLASK_MIGRATION_SUMMARY.md) - Complete migration details
- [FLASK_MIGRATION_SUMMARY.md#migration-path](FLASK_MIGRATION_SUMMARY.md#migration-path-for-existing-deployments) - Step-by-step migration

## 📖 Documentation by Topic

### Application Architecture

- [README.md#features](README.md#features) - Core capabilities
- [FLASK_DEPLOYMENT.md#architecture](FLASK_DEPLOYMENT.md#architecture) - System architecture
- [src/job_finder/](src/job_finder/) - Source code

### Configuration

- [.env.example](.env.example) - Environment variables
- [config/](config/) - YAML configuration files
- [FLASK_DEPLOYMENT.md#configuration](FLASK_DEPLOYMENT.md#configuration) - Configuration guide

### API Reference

- [FLASK_DEPLOYMENT.md#http-api-endpoints](FLASK_DEPLOYMENT.md#http-api-endpoints) - API endpoints
- [QUICK_REFERENCE.md#http-api-endpoints](QUICK_REFERENCE.md#http-api-endpoints) - Quick API reference

### Troubleshooting

- [FLASK_DEPLOYMENT.md#troubleshooting](FLASK_DEPLOYMENT.md#troubleshooting) - Common issues and solutions
- [LOCAL_DEVELOPMENT.md#troubleshooting](LOCAL_DEVELOPMENT.md#troubleshooting) - Development issues
- [QUICK_REFERENCE.md#common-issues--solutions](QUICK_REFERENCE.md#common-issues--solutions) - Quick fixes

### Code Quality

- [TEST_IMPROVEMENTS_FINAL_REPORT.md](TEST_IMPROVEMENTS_FINAL_REPORT.md) - Test coverage and quality
- [LOCAL_DEVELOPMENT.md#code-quality](LOCAL_DEVELOPMENT.md#code-quality) - Linting, formatting, type checking
- [Makefile](Makefile) - Quality check commands

## 📝 Complete File Listing

### Primary Documentation

| File | Description | Audience |
|------|-------------|----------|
| [README.md](README.md) | Project overview | Everyone |
| [FLASK_DEPLOYMENT.md](FLASK_DEPLOYMENT.md) | Deployment guide | DevOps |
| [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) | Development guide | Developers |
| [QUICK_REFERENCE.md](QUICK_REFERENCE.md) | Quick reference | Everyone |

### Migration & Reports

| File | Description | Audience |
|------|-------------|----------|
| [FLASK_MIGRATION_SUMMARY.md](FLASK_MIGRATION_SUMMARY.md) | Docker → Flask migration | DevOps |
| [TEST_IMPROVEMENTS_FINAL_REPORT.md](TEST_IMPROVEMENTS_FINAL_REPORT.md) | Test coverage report | QA, Developers |

### Configuration Examples

| File | Description | Purpose |
|------|-------------|---------|
| [.env.example](.env.example) | Environment variables | Template |
| [config/config.dev.yaml](config/config.dev.yaml) | Development config | Configuration |
| [config/config.prod.yaml](config/config.prod.yaml) | Production config | Configuration |

### Run Scripts

| File | Description | Use Case |
|------|-------------|----------|
| [run_dev.sh](run_dev.sh) | Development runner | Development |
| [run_prod.sh](run_prod.sh) | Production runner | Production |
| [Makefile](Makefile) | Make commands | All |

## 🎯 Quick Navigation

### I want to...

**...set up for development**
→ [LOCAL_DEVELOPMENT.md#initial-setup](LOCAL_DEVELOPMENT.md#initial-setup)

**...deploy to production**
→ [FLASK_DEPLOYMENT.md#production](FLASK_DEPLOYMENT.md#production)

**...run tests**
→ [LOCAL_DEVELOPMENT.md#running-tests](LOCAL_DEVELOPMENT.md#running-tests)

**...add a new feature**
→ [LOCAL_DEVELOPMENT.md#development-tasks](LOCAL_DEVELOPMENT.md#development-tasks)

**...fix a bug**
→ [LOCAL_DEVELOPMENT.md#debugging](LOCAL_DEVELOPMENT.md#debugging)

**...check code quality**
→ [LOCAL_DEVELOPMENT.md#code-quality](LOCAL_DEVELOPMENT.md#code-quality)

**...deploy with systemd**
→ [FLASK_DEPLOYMENT.md#using-systemd](FLASK_DEPLOYMENT.md#using-systemd-recommended-for-production)

**...monitor the worker**
→ [FLASK_DEPLOYMENT.md#monitoring](FLASK_DEPLOYMENT.md#monitoring)

**...understand test coverage**
→ [TEST_IMPROVEMENTS_FINAL_REPORT.md](TEST_IMPROVEMENTS_FINAL_REPORT.md)

**...migrate from Docker**
→ [FLASK_MIGRATION_SUMMARY.md#migration-path](FLASK_MIGRATION_SUMMARY.md#migration-path-for-existing-deployments)

**...get quick help**
→ [QUICK_REFERENCE.md](QUICK_REFERENCE.md)

## 🔍 Search by Keyword

| Keyword | See |
|---------|-----|
| API endpoints | [FLASK_DEPLOYMENT.md#http-api-endpoints](FLASK_DEPLOYMENT.md#http-api-endpoints) |
| CI/CD | [FLASK_MIGRATION_SUMMARY.md#for-cicd-pipelines](FLASK_MIGRATION_SUMMARY.md#for-cicd-pipelines) |
| Configuration | [FLASK_DEPLOYMENT.md#configuration](FLASK_DEPLOYMENT.md#configuration) |
| Debugging | [LOCAL_DEVELOPMENT.md#debugging](LOCAL_DEVELOPMENT.md#debugging) |
| Environment variables | [.env.example](.env.example), [QUICK_REFERENCE.md#environment-variables](QUICK_REFERENCE.md#environment-variables) |
| Firebase | [LOCAL_DEVELOPMENT.md#firebase-setup](LOCAL_DEVELOPMENT.md#firebase-setup) |
| Health checks | [FLASK_DEPLOYMENT.md#health-checks](FLASK_DEPLOYMENT.md#health-checks) |
| Installation | [README.md#setup](README.md#setup) |
| Logging | [FLASK_DEPLOYMENT.md#log-monitoring](FLASK_DEPLOYMENT.md#log-monitoring) |
| Makefile | [Makefile](Makefile), [QUICK_REFERENCE.md#common-commands](QUICK_REFERENCE.md#common-commands) |
| Migration | [FLASK_MIGRATION_SUMMARY.md](FLASK_MIGRATION_SUMMARY.md) |
| Monitoring | [FLASK_DEPLOYMENT.md#monitoring](FLASK_DEPLOYMENT.md#monitoring) |
| PM2 | [FLASK_DEPLOYMENT.md#using-pm2](FLASK_DEPLOYMENT.md#using-pm2-alternative) |
| Production | [FLASK_DEPLOYMENT.md](FLASK_DEPLOYMENT.md) |
| Scaling | [FLASK_DEPLOYMENT.md#scaling](FLASK_DEPLOYMENT.md#scaling) |
| Security | [FLASK_DEPLOYMENT.md#security](FLASK_DEPLOYMENT.md#security) |
| Supervisor | [FLASK_DEPLOYMENT.md#using-supervisor](FLASK_DEPLOYMENT.md#using-supervisor) |
| systemd | [FLASK_DEPLOYMENT.md#using-systemd](FLASK_DEPLOYMENT.md#using-systemd-recommended-for-production) |
| Testing | [LOCAL_DEVELOPMENT.md#running-tests](LOCAL_DEVELOPMENT.md#running-tests) |
| Troubleshooting | [FLASK_DEPLOYMENT.md#troubleshooting](FLASK_DEPLOYMENT.md#troubleshooting) |

## 📦 Archive

Legacy Docker-related documentation and files:

- `.archive/docker/` - Archived Docker files
  - Dockerfile
  - docker-compose.*.yml
  - DOCKER_COMPOSE_GUIDE.md

These are preserved for reference but are no longer used.

## 🆘 Support

### Getting Help

1. **Check documentation** - Use this index to find relevant docs
2. **Check quick reference** - [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common tasks
3. **Check logs** - `make logs` or `tail -f logs/worker.log`
4. **Check health** - `make health` or `curl http://localhost:5555/health`
5. **Run tests** - `make test` to verify functionality

### Common First Steps

```bash
# 1. Check if worker is running
make health

# 2. Check logs for errors
make logs

# 3. Verify configuration
make check-config
make check-env

# 4. Run tests
make test

# 5. Check documentation
cat QUICK_REFERENCE.md
```

## 📊 Documentation Statistics

- **Total documentation files:** 8 primary files
- **Total pages:** ~60 pages
- **Topics covered:** 50+
- **Code examples:** 100+
- **Last updated:** 2025-10-27
- **Documentation type:** Flask Application (No Docker)

## 🔄 Documentation Updates

This documentation is maintained alongside the code. When making changes:

1. Update relevant documentation files
2. Update this index if adding/removing files
3. Update QUICK_REFERENCE.md for command changes
4. Keep examples current with actual code

## ✅ Documentation Completeness

- ✅ Setup and installation
- ✅ Development workflow
- ✅ Testing procedures
- ✅ Deployment options
- ✅ Configuration guide
- ✅ API reference
- ✅ Troubleshooting
- ✅ Migration guide
- ✅ Quick reference
- ✅ Code quality
- ✅ Performance tuning
- ✅ Security guidelines

---

**Last Updated:** 2025-10-27  
**Documentation Version:** 1.0.0  
**Application Type:** Flask (No Docker)  
**Status:** Complete and Current
