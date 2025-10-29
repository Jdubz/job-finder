# Job Finder Documentation

Welcome to the Job Finder documentation. This guide will help you understand, set up, and work with the job-finding system.

## Getting Started

New to Job Finder? Start here:

1. **[Setup Guide](setup.md)** - Complete installation and configuration instructions
2. **[Architecture Overview](architecture.md)** - Understand how the system works
3. **[Development Guide](development.md)** - Contributing and local development workflow

## Core Documentation

### System Architecture
- **[Architecture](../../docs/architecture/worker-architecture.md)** - Complete system design, components, and data flow
- **[Queue System](queue-system.md)** - Queue-based pipeline architecture and processing

### Setup & Configuration
- **[Setup Guide](setup.md)** - Prerequisites, installation, and environment configuration
- **[Deployment Guide](deployment.md)** - Docker deployment with Portainer

### Development
- **[Development Workflow](development.md)** - Local development, testing, and code quality
- **[Next Steps](next-steps.md)** - Roadmap, technical debt, and planned features

### Operations Runbooks
- **[Duplicate Prevention](operations/duplicate-prevention.md)** - Mitigation steps for duplicate content processing
- **[Sync Production Data](operations/sync-production-data.md)** - Refresh local emulator with production-grade content items

### Observability
- **[Structured Logging](observability/structured-logging.md)** - Worker JSON formatter, sampling rules, and troubleshooting
- **[Logging Overview](observability/logging.md)** - Legacy logging practices (update in progress)
- Shared architecture references are mirrored from `docs/shared/job-finder-docs/docs/architecture/structured-logging-overview.md`.

## Specialized Guides

### Integration Guides
- **[job-finder-FE Integration](integrations/portfolio.md)** - Integrate with job-finder-FE web application

### Configuration Guides
- **[Environment Configuration](guides/environments.md)** - Multi-environment setup (staging/production)
- **[Local Testing](guides/local-testing.md)** - Docker local testing with docker-compose
- **[Cloud Logging](guides/cloud-logging.md)** - Google Cloud Logging setup
- **[Scheduler Configuration](SCHEDULER_CONFIG.md)** - Control automated scraping via Firestore
  - **[Quick Reference](SCHEDULER_CONFIG_QUICKREF.md)** - Quick commands for scheduler control

## Reference Documentation

### Historical Context
The [archive](archive/) folder contains historical documents and session notes that provide context for past architectural decisions:

- **[Firestore Cleanup Summary](archive/firestore-cleanup.md)** - Database optimization work
- **[Pipeline Refactor Notes](archive/pipeline-refactor.md)** - Architecture evolution
- **[Session Context](archive/session-context.md)** - Development session notes

## Quick Links

### Common Tasks

**Setup a new environment:**
```bash
# See: docs/setup.md
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Architecture Documentation:**
- [Worker Architecture](../../docs/architecture/worker-architecture.md) - Complete system design
- [System Overview](../../docs/architecture/system-overview.md) - Overall system architecture

**Run the job finder:**
```bash
# See: docs/development.md
python -m job_finder.main
```

**Deploy to production:**
```bash
# See: docs/deployment.md
docker-compose -f docker-compose.production.yml up -d
```

### External Resources

- [Project README](../README.md) - Project overview and quick start
- [Contributing Guidelines](../CONTRIBUTING.md) - How to contribute
- [Claude AI Instructions](../CLAUDE.md) - AI assistant guidance
- [Security Policy](../SECURITY.md) - Security best practices

## Documentation Structure

```
docs/
├── README.md                  # This file - documentation navigation
│
├── architecture.md            # Complete system architecture
├── setup.md                   # Setup and installation guide
├── deployment.md              # Docker deployment guide
├── development.md             # Development workflow
├── queue-system.md            # Queue-based pipeline guide
├── next-steps.md              # Roadmap and technical debt
│
├── guides/                    # Specialized configuration guides
│   ├── environments.md        # Multi-environment configuration
│   ├── local-testing.md       # Docker local testing
│   └── cloud-logging.md       # Cloud logging setup
│
├── observability/             # Logging, metrics, and monitoring guides
│   ├── logging.md
│   └── structured-logging.md
│
├── operations/                # Operations runbooks and on-call procedures
│   ├── duplicate-prevention.md
│   └── sync-production-data.md
│
├── integrations/              # Integration guides
│   └── portfolio.md           # job-finder-FE project integration
│
└── archive/                   # Historical documentation
    ├── firestore-cleanup.md   # Database optimization notes
    ├── pipeline-refactor.md   # Architecture evolution
    └── session-context.md     # Development session context
```

## Need Help?

- Review the [Architecture](architecture.md) to understand the system design
- Check [Setup Guide](setup.md) for installation issues
- See [Development Guide](development.md) for contribution guidelines
- Review [Next Steps](next-steps.md) for known issues and planned improvements

## Contributing to Documentation

When updating documentation:

1. Keep the structure organized (architecture, setup, deployment, development)
2. Update this README.md navigation when adding new documents
3. Ensure all links are relative and working
4. Follow the existing documentation style and format
5. Include code examples and practical usage instructions

---

**Last Updated:** 2025-10-16
