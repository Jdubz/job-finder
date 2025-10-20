# Job Finder Deployment Guide

Complete deployment setup for staging and production environments using Portainer.

---

## 📋 Overview

This project supports **two separate environments**:

| Environment | Database | Purpose | Auto-Update |
|------------|----------|---------|-------------|
| **Staging** | `portfolio-staging` | Testing & Development | Every 3 min |
| **Production** | `portfolio` | Live Job Searches | Every 5 min |

Both environments run **isolated containers** with separate:
- Databases (staging vs production)
- Configurations
- Logs and data directories
- Resource allocations
- Networks

---

## 🚀 Quick Start

**⏱️ 5-minute deployment** → See **[PORTAINER_QUICK_START.md](docs/PORTAINER_QUICK_START.md)**

### Prerequisites

- Portainer running
- Firebase service account JSON
- Anthropic API key
- Docker installed on server

### Deployment Commands

```bash
# 1. Prepare directories
mkdir -p ~/job-finder-staging/{credentials,config,logs-staging,data-staging}
mkdir -p ~/job-finder-production/{credentials,config,logs,data}

# 2. Upload credentials
scp serviceAccountKey.json user@server:~/job-finder-staging/credentials/
scp serviceAccountKey.json user@server:~/job-finder-production/credentials/

# 3. Deploy in Portainer UI
# - Create "job-finder-staging" stack from docker-compose.staging.yml
# - Create "job-finder-production" stack from docker-compose.production.yml

# 4. Verify deployment
docker logs job-finder-staging --tail 20
docker logs job-finder-production --tail 20
```

---

## 📚 Documentation

### Deployment Guides

1. **[BRANCHING_STRATEGY.md](docs/BRANCHING_STRATEGY.md)** ⭐ **START HERE**
   - Git workflow and branch strategy
   - Development workflow
   - Deployment automation
   - Common scenarios

2. **[PORTAINER_QUICK_START.md](docs/PORTAINER_QUICK_START.md)**
   - 5-minute quick start guide
   - Step-by-step Portainer setup
   - Common issues & fixes

3. **[PORTAINER_DEPLOYMENT_GUIDE.md](docs/PORTAINER_DEPLOYMENT_GUIDE.md)**
   - Complete deployment reference
   - Architecture overview
   - Volume mapping strategy
   - Network isolation
   - Auto-update configuration
   - Monitoring & troubleshooting

4. **[STAGING_VS_PRODUCTION.md](docs/STAGING_VS_PRODUCTION.md)**
   - Detailed environment comparison
   - Resource allocation differences
   - Configuration differences
   - Data lifecycle
   - Migration procedures

### Configuration Guides

4. **[PRODUCTION_QUEUE_TROUBLESHOOTING.md](docs/PRODUCTION_QUEUE_TROUBLESHOOTING.md)**
   - Queue setup guide
   - Database configuration fixes
   - Security rules setup

5. **[FRONTEND_CONFIG.md](docs/FRONTEND_CONFIG.md)**
   - job-finder-FE frontend setup
   - Environment-based database selection
   - Firestore security rules

### Environment Templates

6. **[.env.staging.example](.env.staging.example)**
   - Staging environment variables template

7. **[.env.production.example](.env.production.example)**
   - Production environment variables template

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Portainer Server                          │
├──────────────────────────┬──────────────────────────────────┤
│   STAGING STACK          │   PRODUCTION STACK               │
├──────────────────────────┼──────────────────────────────────┤
│ Container:               │ Container:                       │
│ ├─ job-finder-staging    │ ├─ job-finder-production         │
│ ├─ watchtower-staging    │ ├─ watchtower-production         │
│                          │                                  │
│ Database:                │ Database:                        │
│ └─ portfolio-staging     │ └─ portfolio                     │
│                          │                                  │
│ Resources:               │ Resources:                       │
│ ├─ 1 CPU / 1GB RAM      │ ├─ 1.5 CPU / 1.5GB RAM          │
│ └─ Update: 3min          │ └─ Update: 5min                  │
│                          │                                  │
│ Volumes:                 │ Volumes:                         │
│ ├─ credentials/          │ ├─ credentials/                  │
│ ├─ config/               │ ├─ config/                       │
│ ├─ logs-staging/         │ ├─ logs/                         │
│ └─ data-staging/         │ └─ data/                         │
└──────────────────────────┴──────────────────────────────────┘
```

---

## 📦 Files

### Docker Compose Files

- `docker-compose.staging.yml` - Staging environment configuration
- `docker-compose.production.yml` - Production environment configuration

### Configuration Files

- `config/config.yaml` - Staging configuration (default)
- `config/config.production.yaml` - Production configuration

### Diagnostic Scripts

- `scripts/setup_production_queue.py` - Initialize queue collection
- `scripts/diagnose_production_queue.py` - Verify database setup

---

## 🔧 Common Tasks

### View Logs

```bash
# Staging
docker logs -f job-finder-staging

# Production
docker logs -f job-finder-production
```

### Restart Container

```bash
# Staging
docker restart job-finder-staging

# Production
docker restart job-finder-production
```

### Check Database Configuration

```bash
# Staging
docker exec job-finder-staging env | grep DATABASE

# Production
docker exec job-finder-production env | grep DATABASE
```

### Run Diagnostics

```bash
# Staging
docker exec -it job-finder-staging \
  python scripts/diagnose_production_queue.py --database portfolio-staging

# Production
docker exec -it job-finder-production \
  python scripts/diagnose_production_queue.py --database portfolio
```

### Monitor Resources

```bash
docker stats job-finder-staging job-finder-production
```

---

## 🔄 Deployment Workflow

### Standard Workflow

```
1. Work on 'staging' branch → Push changes
          ↓
2. GitHub Actions → Build Docker image (:staging tag)
          ↓
3. Watchtower → Auto-deploy to STAGING (3min)
          ↓
4. Test in staging environment
          ↓
5. Create PR: staging → main → Merge
          ↓
6. GitHub Actions → Build Docker image (:latest tag)
          ↓
7. Watchtower → Auto-deploy to PRODUCTION (5min)
          ↓
8. Verify in production
```

**See [BRANCHING_STRATEGY.md](docs/BRANCHING_STRATEGY.md) for complete workflow details.**

### Hotfix Workflow

```
1. Fix issue → Push to 'main' directly
          ↓
2. Auto-deploy to production (5min)
          ↓
3. Verify fix → Backport to 'develop'
```

---

## 🔐 Security

### API Keys

- Store in Portainer environment variables (not in code)
- Use separate keys for staging and production
- Use production-tier keys for production environment

### Credentials

```bash
# Proper permissions
chmod 600 credentials/serviceAccountKey.json
```

### Networks

- Staging and production use isolated networks
- No cross-environment communication
- Security boundary between environments

---

## 📊 Monitoring

### Health Checks

Both environments have automatic health checks:
- Interval: 5 minutes
- Retries: 3
- Auto-restart on failure

### Watchtower Notifications (Optional)

Set in Portainer environment variables:

```
WATCHTOWER_NOTIFICATION_URL=discord://webhook_token@webhook_id
```

Supported:
- Discord
- Slack
- Email
- And more via Shoutrrr

---

## 🆘 Troubleshooting

### Container Not Starting

1. Check logs: `docker logs job-finder-staging`
2. Verify credentials exist
3. Check API keys in Portainer
4. Verify volume paths

### Queue Items Not Processing

1. Check database name: `docker exec job-finder-staging env | grep DATABASE`
2. Verify job-finder-FE frontend configuration
3. Run diagnostic script
4. Check Firestore security rules

### Different Behavior Between Environments

1. Compare configurations
2. Check database names
3. Verify API key tiers
4. Review resource allocations

**See [PRODUCTION_QUEUE_TROUBLESHOOTING.md](docs/PRODUCTION_QUEUE_TROUBLESHOOTING.md) for detailed troubleshooting.**

---

## 📈 Resource Planning

### Staging Resources

- **CPU:** 1.0 limit, 0.25 reserved
- **Memory:** 1GB limit, 256MB reserved
- **Purpose:** Cost-effective testing
- **Expected load:** Low (testing only)

### Production Resources

- **CPU:** 1.5 limit, 0.5 reserved
- **Memory:** 1.5GB limit, 512MB reserved
- **Purpose:** Reliable performance
- **Expected load:** Medium (real job searches)

**Adjust based on actual usage patterns.**

---

## 🔄 Updates & Maintenance

### Automatic Updates

**Watchtower** handles automatic deployments:

- **Staging:** Checks every 3 minutes
- **Production:** Checks every 5 minutes

### Manual Updates

```bash
# In Portainer UI
Stacks → Select stack → Click "Update the stack"

# Or via CLI
docker pull ghcr.io/jdubz/job-finder:latest
docker restart job-finder-production
```

### Configuration Updates

1. Edit config file on server
2. Restart container in Portainer
3. Verify changes in logs

---

## 📝 Environment Variables

### Required (Set in Portainer)

```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
OPENAI_API_KEY=sk-...  # Optional
```

### Optional (Set in Portainer)

```bash
WATCHTOWER_NOTIFICATION_URL=discord://...
```

### Pre-configured (In docker-compose.yml)

```bash
# Staging
PROFILE_DATABASE_NAME=portfolio-staging
STORAGE_DATABASE_NAME=portfolio-staging

# Production
PROFILE_DATABASE_NAME=portfolio
STORAGE_DATABASE_NAME=portfolio
```

---

## ✅ Deployment Checklist

### Initial Setup

- [ ] Create server directories
- [ ] Upload Firebase credentials
- [ ] Set API keys in Portainer
- [ ] Deploy staging stack
- [ ] Deploy production stack
- [ ] Verify both containers running
- [ ] Check database connections
- [ ] Test queue processing

### Before Each Deploy

- [ ] Test in staging
- [ ] Check staging logs
- [ ] Verify no errors
- [ ] Review configuration changes
- [ ] Prepare rollback plan

### After Each Deploy

- [ ] Verify container started
- [ ] Check logs for errors
- [ ] Test queue processing
- [ ] Monitor resource usage
- [ ] Verify health checks passing

---

## 🔗 Related Documentation

- **[CLAUDE.md](CLAUDE.md)** - Project overview and architecture
- **[docs/setup.md](docs/setup.md)** - Local development setup
- **[docs/queue-system.md](docs/queue-system.md)** - Queue processing details
- **[docs/integrations/portfolio.md](docs/integrations/portfolio.md)** - job-finder-FE integration

---

## 📞 Support

For deployment issues:

1. Check relevant documentation above
2. Run diagnostic scripts
3. Review container logs
4. Verify configuration

**Quick Start:** [PORTAINER_QUICK_START.md](docs/PORTAINER_QUICK_START.md)
