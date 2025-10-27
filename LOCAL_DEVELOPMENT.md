# Local Development Guide

Complete guide for developing the Job Finder Worker locally.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git
- Firebase project with Firestore enabled
- API key (Anthropic Claude or OpenAI GPT)

## Initial Setup

### 1. Clone and Set Up Environment

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd job-finder-worker

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-test.txt
```

### 2. Firebase Setup

1. **Create Firebase Project** (if needed):
   - Go to https://console.firebase.google.com/
   - Create a new project or use existing
   - Enable Firestore database

2. **Generate Service Account Key**:
   - Go to Project Settings → Service Accounts
   - Click "Generate New Private Key"
   - Save as `credentials/firebase-key.json`

3. **Set Environment Variable**:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/credentials/firebase-key.json"
   
   # Add to your shell profile for persistence
   echo 'export GOOGLE_APPLICATION_CREDENTIALS="/full/path/to/firebase-key.json"' >> ~/.bashrc
   ```

### 3. API Keys

Get an API key from one of:

**Option A: Anthropic Claude (Recommended)**
- Sign up at https://console.anthropic.com/
- Create an API key
- Add to `.env`: `ANTHROPIC_API_KEY=your_key_here`

**Option B: OpenAI GPT**
- Sign up at https://platform.openai.com/
- Create an API key
- Add to `.env`: `OPENAI_API_KEY=your_key_here`

### 4. Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your keys
nano .env  # or use your preferred editor

# Configure the worker
cp config/config.example.yaml config/config.dev.yaml
nano config/config.dev.yaml
```

## Development Workflow

### Starting the Worker

```bash
# Method 1: Using run script (recommended)
./run_dev.sh

# Method 2: Using make
make dev

# Method 3: Direct Python
source venv/bin/activate
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"
python3 -m job_finder.flask_worker
```

The worker starts on `http://127.0.0.1:5555`

### Monitoring the Worker

**Terminal 1: Run the worker**
```bash
./run_dev.sh
```

**Terminal 2: Monitor logs**
```bash
tail -f logs/worker.log

# Or with JSON formatting
tail -f logs/worker.log | jq '.'

# Or using make
make logs
make logs-json
```

**Terminal 3: Test endpoints**
```bash
# Health check
curl http://localhost:5555/health | jq '.'

# Status
curl http://localhost:5555/status | jq '.'

# Or using make
make health
make status
```

### Running Tests

```bash
# Run all tests
make test

# Run tests with coverage
make coverage

# Run tests without coverage (faster)
make test-fast

# Run specific test file
pytest tests/test_rss_scraper.py -v

# Run specific test
pytest tests/test_rss_scraper.py::TestRSSJobScraperInit::test_init_stores_config -v

# Run tests matching a pattern
pytest -k "scraper" -v
```

### Code Quality

```bash
# Run linter
make lint

# Format code
make format

# Type check
make type-check

# All checks
make lint && make type-check && make test
```

## Development Tasks

### Adding a New Scraper

1. **Create scraper class** in `src/job_finder/scrapers/`:
   ```python
   from .base import BaseScraper
   
   class MyNewScraper(BaseScraper):
       def scrape(self) -> List[Dict[str, Any]]:
           # Implementation
           pass
   ```

2. **Add tests** in `tests/test_my_new_scraper.py`:
   ```python
   import pytest
   from job_finder.scrapers.my_new_scraper import MyNewScraper
   
   def test_scraper_init():
       scraper = MyNewScraper(config={})
       assert scraper is not None
   ```

3. **Run tests**:
   ```bash
   pytest tests/test_my_new_scraper.py -v
   ```

### Modifying the Queue Processor

1. Edit `src/job_finder/job_queue/processor.py`
2. Add tests in `tests/queue/test_processor.py`
3. Run specific tests:
   ```bash
   pytest tests/queue/test_processor.py -v
   ```

### Adding New API Endpoints

1. Edit `src/job_finder/flask_worker.py`
2. Add endpoint:
   ```python
   @app.route("/my-endpoint")
   def my_endpoint():
       return jsonify({"message": "Hello"})
   ```
3. Test manually:
   ```bash
   curl http://localhost:5555/my-endpoint
   ```

## Debugging

### Using pdb (Python Debugger)

Add breakpoint in code:
```python
import pdb; pdb.set_trace()
```

Or use the built-in breakpoint():
```python
breakpoint()  # Python 3.7+
```

### Using VS Code Debugger

Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Flask Worker",
            "type": "python",
            "request": "launch",
            "module": "job_finder.flask_worker",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src",
                "GOOGLE_APPLICATION_CREDENTIALS": "${workspaceFolder}/credentials/firebase-key.json"
            },
            "console": "integratedTerminal"
        },
        {
            "name": "Pytest",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "-v",
                "${file}"
            ],
            "env": {
                "PYTHONPATH": "${workspaceFolder}/src"
            },
            "console": "integratedTerminal"
        }
    ]
}
```

### Verbose Logging

```bash
# Set log level in .env
LOG_LEVEL=DEBUG

# Or export for current session
export LOG_LEVEL=DEBUG
./run_dev.sh
```

### Testing with Mock Data

Create test fixtures in `tests/fixtures/`:
```python
# tests/fixtures/mock_jobs.py
MOCK_JOB = {
    "title": "Software Engineer",
    "company": "Test Company",
    "description": "Test description",
    "url": "https://example.com/job"
}
```

Use in tests:
```python
from tests.fixtures.mock_jobs import MOCK_JOB

def test_something():
    job = MOCK_JOB.copy()
    # Test with mock data
```

## Common Development Tasks

### Reset Everything

```bash
# Stop the worker
make shutdown

# Clean all generated files
make clean-all

# Reinstall
make install

# Restart
make dev
```

### Update Dependencies

```bash
# Update requirements.txt
pip install --upgrade <package>
pip freeze > requirements.txt

# Or update all
pip install --upgrade -r requirements.txt
```

### Database Reset (Development)

```bash
# Clear Firestore collections (CAUTION!)
# Create a script: scripts/clear_dev_data.py
python3 scripts/clear_dev_data.py
```

### Generate Test Coverage Report

```bash
# Generate HTML coverage report
make coverage

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## IDE Setup

### VS Code Extensions

Recommended extensions:
- Python (Microsoft)
- Pylance (Microsoft)
- Python Test Explorer
- Python Docstring Generator
- GitLens

### VS Code Settings

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests",
        "-v"
    ],
    "python.linting.enabled": true,
    "python.linting.flake8Enabled": true,
    "python.formatting.provider": "black",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

### PyCharm Setup

1. Open project
2. Configure interpreter: Settings → Project → Python Interpreter
3. Select existing venv: `<project>/venv/bin/python`
4. Configure pytest: Settings → Tools → Python Integrated Tools
5. Set test runner to "pytest"

## Troubleshooting

### Import Errors

```bash
# Make sure PYTHONPATH is set
export PYTHONPATH="${PWD}/src:${PYTHONPATH}"

# Or use the run scripts which set it automatically
./run_dev.sh
```

### Firebase Connection Issues

```bash
# Check credentials file
ls -la $GOOGLE_APPLICATION_CREDENTIALS

# Test connection
python3 -c "from google.cloud import firestore; db = firestore.Client(); print('Connected!')"
```

### Port Already in Use

```bash
# Find process using port 5555
lsof -i :5555

# Kill the process
kill -9 <PID>

# Or use different port
WORKER_PORT=5556 ./run_dev.sh
```

### Tests Failing

```bash
# Run with verbose output
pytest -vv

# Run with print statements shown
pytest -s

# Run specific failing test
pytest tests/test_file.py::TestClass::test_method -vv

# Drop into debugger on failure
pytest --pdb
```

## Performance Optimization

### Reduce Startup Time

```bash
# Use faster config loading
# Cache compiled Python files
python3 -OO -m job_finder.flask_worker
```

### Speed Up Tests

```bash
# Run tests in parallel
pytest -n auto

# Run only modified tests
pytest --lf  # last failed
pytest --ff  # failed first
```

### Profile Code

```python
# Add profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes and test
make test
make lint

# Commit
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/my-feature
```

## Best Practices

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings
- Keep functions small (<50 lines)
- Meaningful variable names

### Testing

- Write tests first (TDD)
- Test happy path + errors + edge cases
- Use descriptive test names
- Keep tests fast (<1s each)
- Mock external dependencies

### Commits

- Use conventional commits (feat:, fix:, docs:, test:)
- Keep commits atomic
- Write clear commit messages
- Reference issues in commits

## Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Python Style Guide](https://pep8.org/)
- [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup)

## Getting Help

1. Check logs: `make logs`
2. Review documentation in `docs/`
3. Check test examples in `tests/`
4. See FLASK_DEPLOYMENT.md for deployment issues

---

**Last Updated:** 2025-10-27  
**For:** Local Development  
**Environment:** Flask (No Docker)
