# Environment Setup - Quick Reference

## At a Glance

### Local Development
```bash
# Uses portfolio-staging database
python run_job_search.py
```

**Database**: `portfolio-staging` (both profile and job storage)
**Config**: `config/config.yaml`
**Safe for**: Testing, development, experimentation

---

### Docker Staging
```bash
# Deploy staging container
docker-compose up -d
```

**Container**: `job-finder-staging`
**Database**: `portfolio-staging` (both profile and job storage)
**Config**: `config/config.yaml`
**Environment Variables**:
- `PROFILE_DATABASE_NAME=portfolio-staging`
- `STORAGE_DATABASE_NAME=portfolio-staging`

---

### Docker Production
```bash
# Deploy production container
docker-compose -f docker-compose.production.yml up -d
```

**Container**: `job-finder-production`
**Database**: `portfolio` (both profile and job storage)
**Config**: `config/config.production.yaml`
**Environment Variables**:
- `PROFILE_DATABASE_NAME=portfolio`
- `STORAGE_DATABASE_NAME=portfolio`

---

## Key Points

✅ **Local development always uses `portfolio-staging`**
- Configured in `config/config.yaml`
- Safe for testing
- Won't affect production data

✅ **Production container always uses `portfolio`**
- Uses `docker-compose.production.yml`
- Environment variables override config
- Live job searches

✅ **Environment variables take precedence**
- Override config file settings
- Makes switching environments easy
- Set in docker-compose files

---

## Files

| File | Purpose | Database |
|------|---------|----------|
| `config/config.yaml` | Local dev & staging | `portfolio-staging` |
| `config/config.production.yaml` | Production | `portfolio` |
| `docker-compose.yml` | Staging container | `portfolio-staging` |
| `docker-compose.production.yml` | Production container | `portfolio` |

---

## Verification

### Check which database you're using:

**Local**:
```bash
grep database_name config/config.yaml
```

**Docker**:
```bash
docker exec job-finder-staging env | grep DATABASE_NAME
# or
docker exec job-finder-production env | grep DATABASE_NAME
```

---

## Full Documentation

- **Complete guide**: [ENVIRONMENTS.md](ENVIRONMENTS.md)
- **Docker deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Quick start**: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)
