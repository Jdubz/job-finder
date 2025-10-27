# Job Finder Worker - Quick Reference

**Flask Application (No Docker)** - One-page developer reference

## Quick Start

```bash
# First time setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your keys
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/credentials/firebase-key.json"

# Start worker
./run_dev.sh        # Development mode
./run_prod.sh       # Production mode
make dev            # Using make
```

## Common Commands

| Command | Description |
|---------|-------------|
| `make dev` | Start worker (development) |
| `make prod` | Start worker (production) |
| `make test` | Run all tests |
| `make coverage` | Run tests with coverage |
| `make lint` | Run code linter |
| `make health` | Check worker health |
| `make status` | Get worker status |
| `make shutdown` | Stop worker gracefully |
| `make logs` | Tail worker logs |
| `make clean` | Clean generated files |

## HTTP API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/status` | GET | Detailed status |
| `/shutdown` | POST | Graceful shutdown |

```bash
curl http://localhost:5555/health
curl http://localhost:5555/status
curl -X POST http://localhost:5555/shutdown
```

## File Structure

```
job-finder-worker/
├── src/job_finder/          # Main application code
│   ├── flask_worker.py      # Flask worker entry point
│   ├── scrapers/            # Job scrapers
│   ├── filters/             # Job filters
│   ├── job_queue/           # Queue processing
│   ├── storage/             # Firestore storage
│   └── ai/                  # AI matching
├── tests/                   # Test files
├── config/                  # Configuration files
│   ├── config.dev.yaml      # Development config
│   └── config.prod.yaml     # Production config
├── logs/                    # Log files
├── run_dev.sh               # Development runner
├── run_prod.sh              # Production runner
├── Makefile                 # Make commands
└── .env                     # Environment variables
```

## Environment Variables

### Required
```bash
GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-key.json
ANTHROPIC_API_KEY=your_claude_key  # or OPENAI_API_KEY
```

### Optional
```bash
WORKER_PORT=5555               # Default: 5555
WORKER_HOST=127.0.0.1          # Default: 127.0.0.1 (dev), 0.0.0.0 (prod)
POLL_INTERVAL=60               # Default: 60 seconds
LOG_LEVEL=INFO                 # DEBUG, INFO, WARNING, ERROR
QUEUE_WORKER_LOG_FILE=logs/worker.log
PROFILE_DATABASE_NAME=job-finder-staging
STORAGE_DATABASE_NAME=job-finder-staging
```

## Development Workflow

```bash
# 1. Start worker
make dev

# 2. In another terminal, monitor logs
make logs

# 3. Make changes to code
vim src/job_finder/scrapers/my_scraper.py

# 4. Run tests
make test

# 5. Check coverage
make coverage

# 6. Restart worker (Ctrl+C then make dev)
```

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_rss_scraper.py

# Run specific test
pytest tests/test_rss_scraper.py::TestRSSJobScraperInit::test_init_stores_config

# Run with coverage
pytest --cov=src/job_finder --cov-report=html

# Run tests matching pattern
pytest -k "scraper"

# Run verbose
pytest -vv

# Run with output
pytest -s
```

## Debugging

```bash
# Add breakpoint in code
breakpoint()  # Python 3.7+

# Or use pdb
import pdb; pdb.set_trace()

# Run with debugger
python3 -m pdb -m job_finder.flask_worker

# Check logs
tail -f logs/worker.log | jq '.'

# Verbose logging
export LOG_LEVEL=DEBUG
./run_dev.sh
```

## Common Issues & Solutions

### "Port already in use"
```bash
lsof -i :5555  # Find process
kill -9 <PID>  # Kill it
# Or use different port
WORKER_PORT=5556 ./run_dev.sh
```

### "Module not found"
```bash
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
# Or use run scripts which set this automatically
```

### "Firebase connection error"
```bash
# Check credentials
ls -la $GOOGLE_APPLICATION_CREDENTIALS
# Test connection
python3 -c "from google.cloud import firestore; db = firestore.Client(); print('OK')"
```

### "Tests failing"
```bash
# Clean and reinstall
make clean
pip install -r requirements.txt
pytest -vv
```

## Code Style

```python
# Use type hints
def scrape_jobs(url: str) -> List[Dict[str, Any]]:
    pass

# Write docstrings
def parse_job(data: dict) -> Optional[Job]:
    """
    Parse job data from API response.
    
    Args:
        data: Raw job data dict
        
    Returns:
        Parsed Job object or None if invalid
    """
    pass

# Use fixtures in tests
@pytest.fixture
def mock_job():
    return {"title": "Engineer", "company": "ACME"}

def test_parse_job(mock_job):
    result = parse_job(mock_job)
    assert result is not None
```

## Git Workflow

```bash
# Create branch
git checkout -b feature/my-feature

# Make changes and test
make test && make lint

# Commit
git commit -m "feat: add new scraper"

# Push
git push origin feature/my-feature
```

## Performance

```bash
# Profile code
python3 -m cProfile -o profile.stats -m job_finder.flask_worker

# View profile
python3 -m pstats profile.stats
> sort cumulative
> stats 20

# Run tests in parallel
pytest -n auto
```

## Monitoring in Production

```bash
# Using systemd
sudo systemctl status job-finder-worker
sudo journalctl -u job-finder-worker -f

# Check health
curl http://localhost:5555/health | jq '.status'

# Get stats
curl http://localhost:5555/status | jq '.stats'
```

## Useful Aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias jfw='cd /path/to/job-finder-worker'
alias jfw-start='jfw && make dev'
alias jfw-test='jfw && make test'
alias jfw-logs='jfw && make logs'
alias jfw-health='curl -s http://localhost:5555/health | jq .'
```

## Documentation

| File | Description |
|------|-------------|
| `README.md` | General overview |
| `LOCAL_DEVELOPMENT.md` | Development guide |
| `FLASK_DEPLOYMENT.md` | Deployment guide |
| `TEST_IMPROVEMENTS_FINAL_REPORT.md` | Test coverage report |

## Key Directories

| Path | Purpose |
|------|---------|
| `src/job_finder/` | Application code |
| `tests/` | Test files |
| `config/` | YAML config files |
| `logs/` | Log files |
| `credentials/` | Firebase keys (gitignored) |
| `.archive/` | Archived files (Docker, etc.) |

## Support

1. Check logs: `make logs`
2. Review docs: `LOCAL_DEVELOPMENT.md`
3. Run tests: `make test`
4. Check health: `make health`

---

**Version:** 1.0.0  
**Type:** Flask Application (No Docker)  
**Updated:** 2025-10-27
