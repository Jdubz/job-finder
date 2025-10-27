# Job Finder

A Python-based web scraper that finds online job postings relevant to your experience and requirements.

## Legal Disclaimer

**IMPORTANT**: This tool is for **personal, non-commercial use only**. By using this software, you acknowledge that:

- You are responsible for complying with all applicable laws and website Terms of Service
- Web scraping may violate the Terms of Service of some websites
- Use of this tool may result in account suspension or IP blocking
- The maintainers are not liable for any consequences of using this software
- This tool should not be used for commercial data harvesting, credential testing, or malicious purposes

**Always review and comply with each website's Terms of Service and robots.txt before scraping.**

## Features

### Core Capabilities
- **AI-Powered Job Matching**: Uses Claude or GPT-4 to analyze job fit based on your complete profile
- **Resume Intake Generation**: Automatically creates structured data for tailoring resumes to specific jobs
- **Match Scoring**: Assigns 0-100 match scores based on skills, experience, and job requirements
- **Application Prioritization**: Categorizes jobs as High/Medium/Low priority
- **Customization Recommendations**: Provides specific guidance for tailoring each application

### Traditional Features
- Scrapes multiple job boards (LinkedIn, Indeed, etc.)
- Filters jobs based on keywords, experience, and location
- Configurable exclusion criteria
- Multiple output formats (JSON, CSV, database)
- Extensible architecture for adding new job sites

## Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Add your AI API key (required for AI matching)
   # ANTHROPIC_API_KEY=your_key_here (get from https://console.anthropic.com/)
   # or
   # OPENAI_API_KEY=your_key_here (get from https://platform.openai.com/)
   ```

4. **Set up your profile** (choose one option):

   **Option A: Use Firestore (recommended if you have the job-finder-FE frontend)**
   ```bash
   # Download your Firebase service account key from Firebase Console
   # Place it in a secure location (e.g., ~/.firebase/job-finder-key.json)

   # In .env, set:
   # GOOGLE_APPLICATION_CREDENTIALS=/path/to/serviceAccountKey.json

   # In config/config.yaml, set:
   # profile:
   #   source: "firestore"
   #   firestore:
   #     database_name: "job-finder"
   #     name: "Your Name"
   #     email: "your.email@example.com"
   ```

   **Option B: Use JSON profile**
   ```bash
   python -m job_finder.main --create-profile data/profile.json
   # Edit data/profile.json with your experience, skills, and preferences

   # In config/config.yaml, set:
   # profile:
   #   source: "json"
   #   profile_path: "data/profile.json"
   ```

5. **Configure your preferences:**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config/config.yaml:
   # - Set profile source (firestore or json)
   # - Configure AI settings (provider, model, match threshold)
   # - Configure job sites and scraping settings
   ```

## Usage

### Quick Start (Flask Worker)

The worker runs as a Flask application that processes queue items in the background.

**Development Mode:**
```bash
# Start the worker
./run_dev.sh

# Or using make
make dev
```

The worker will start on `http://127.0.0.1:5555` with endpoints:
- `GET /health` - Health check
- `GET /status` - Detailed status
- `POST /shutdown` - Graceful shutdown

**Production Mode:**
```bash
# Set up environment
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/firebase-key.json

# Start the worker
./run_prod.sh

# Or using make
make prod
```

### Worker Control

**Check Health:**
```bash
curl http://localhost:5555/health
# Or: make health
```

**Get Status:**
```bash
curl http://localhost:5555/status
# Or: make status
```

**Graceful Shutdown:**
```bash
curl -X POST http://localhost:5555/shutdown
# Or: make shutdown
```

**View Logs:**
```bash
tail -f logs/worker.log
# Or: make logs
```

### Manual Job Search (One-time run)

Run the job search once without starting the worker:
```bash
python -m job_finder.main
```

Use a custom configuration:
```bash
python -m job_finder.main --config path/to/config.yaml
```

Override output location:
```bash
python -m job_finder.main --output data/my_jobs.json
```

### Profile Management

Create a new profile template:
```bash
python -m job_finder.main --create-profile data/profile.json
```

### Output Structure

When AI matching is enabled, each job in the output includes:
```json
{
  "title": "Software Engineer",
  "company": "Tech Company",
  "location": "Remote",
  "description": "...",
  "url": "https://...",
  "ai_analysis": {
    "match_score": 85,
    "matched_skills": ["Python", "Django", "PostgreSQL"],
    "missing_skills": ["Kubernetes"],
    "application_priority": "High",
    "key_strengths": ["Deep Python expertise", "..."],
    "customization_recommendations": {
      "resume_focus": ["Highlight API development", "..."],
      "cover_letter_points": ["Mention scalability experience", "..."]
    },
    "resume_intake_data": {
      "target_summary": "...",
      "skills_priority": ["Python", "Django", "..."],
      "experience_highlights": [...],
      "keywords_to_include": [...]
    }
  }
}
```

The `resume_intake_data` can be fed directly into resume generation systems.

## Development

### Setup Development Environment

Install development dependencies:
```bash
pip install -r requirements.txt
```

### Pre-commit Hooks (Recommended)

Install pre-commit hooks to automatically check code before commits:
```bash
pip install pre-commit
pre-commit install
```

This will automatically run on every commit:
- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **bandit**: Security checks
- **trailing whitespace**: Remove trailing spaces
- **end-of-file-fixer**: Ensure files end with newline
- **check-yaml**: Validate YAML syntax

Run manually on all files:
```bash
pre-commit run --all-files
```

### Manual Code Quality Checks

Run tests:
```bash
pytest
```

Format code:
```bash
black src/ tests/
```

Sort imports:
```bash
isort src/ tests/
```

Run linter:
```bash
flake8 src/ tests/
```

Type checking:
```bash
mypy src/
```

Security check:
```bash
bandit -r src/
```

## Project Structure

```
job-finder/
├── src/job_finder/        # Main package
│   ├── ai/                # AI-powered job matching
│   │   ├── matcher.py     # Job analysis and intake generation
│   │   ├── providers.py   # AI provider abstraction (Claude, OpenAI)
│   │   └── prompts.py     # Prompt templates
│   ├── profile/           # User profile management
│   │   ├── schema.py      # Profile data models
│   │   └── loader.py      # Profile loading/saving
│   ├── scrapers/          # Site-specific scrapers
│   ├── filters.py         # Traditional job filtering logic
│   ├── storage.py         # Data storage handlers
│   └── main.py            # Entry point and pipeline
├── tests/                 # Test suite
├── config/                # Configuration files
│   └── config.example.yaml
├── data/                  # Output data and profiles
│   └── profile.example.json
└── logs/                  # Application logs
```

## How It Works

1. **Profile Loading**:
   - **Option A**: Load directly from Firestore database (automatically syncs with job-finder-FE frontend)
   - **Option B**: Load from JSON file (manual profile creation)
2. **Job Scraping**: Scrapers collect job postings from configured job boards
3. **Basic Filtering**: Traditional filters remove obviously irrelevant jobs (wrong location, missing keywords)
4. **AI Analysis**: For each remaining job:
   - Analyzes job description against your complete profile
   - Generates a 0-100 match score
   - Identifies which of your skills match and which are missing
   - Determines application priority (High/Medium/Low)
5. **Intake Generation**: For high-scoring jobs:
   - Creates tailored professional summary
   - Prioritizes relevant skills to emphasize
   - Identifies which experiences and projects to highlight
   - Suggests achievement angles and keywords to include
6. **Output**: Saves all data in JSON/CSV format with full AI analysis

## Firestore Integration

If you have the job-finder-FE frontend with Firestore, you can load profile data directly from your database:

**Collections Used:**
- `experience-entries`: Work experience data
- `experience-blurbs`: Skills and highlights

**Benefits:**
- No manual data export/import needed
- Profile automatically stays in sync with job-finder-FE frontend
- Single source of truth for your professional data

**Setup:**
1. Download Firebase service account key from [Firebase Console](https://console.firebase.google.com/)
2. Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
3. Configure `profile.source: "firestore"` in `config.yaml`
4. Run the job finder - it will automatically load your latest profile data

## AI Providers

Job Finder supports multiple AI providers:

- **Anthropic Claude** (recommended): `claude-3-5-sonnet-20241022`
  - More thorough analysis
  - Better at understanding context
  - Get API key: https://console.anthropic.com/

- **OpenAI GPT-4**: `gpt-4o`
  - Fast and reliable
  - Good for high-volume processing
  - Get API key: https://platform.openai.com/

Configure your preferred provider in `config/config.yaml` under the `ai` section.

## Responsible Use Guidelines

### Before You Start

1. **Review Terms of Service**: Check each job board's ToS to ensure scraping is allowed
2. **Check robots.txt**: Verify that automated access is permitted
3. **Use Appropriate Rate Limiting**: Respect server resources with reasonable delays
4. **Personal Use Only**: Do not use for commercial purposes or data resale
5. **Respect Privacy**: Handle any collected data responsibly and in compliance with regulations
6. **API Costs**: Be aware that AI providers charge per API call - monitor your usage

### What NOT to Do

- Do not use for bulk data harvesting or commercial purposes
- Do not circumvent rate limits or access controls
- Do not use for credential testing or unauthorized access
- Do not scrape sites that explicitly prohibit automated access
- Do not share or sell scraped data

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

### Getting Started
- **[Setup Guide](docs/setup.md)** - Complete installation and configuration instructions
- **[Development Workflow](docs/development.md)** - Local development, testing, and code quality

### Architecture & Design
- **[System Architecture](docs/architecture.md)** - Complete system design, components, and data flow
- **[Queue System](docs/queue-system.md)** - Queue-based pipeline architecture and processing
- **[State-Driven Pipeline](docs/STATE_DRIVEN_PIPELINE_SUMMARY.md)** - 🆕 Intelligent, self-healing pipeline design
- **[Loop Prevention](docs/LOOP_PREVENTION_SUMMARY.md)** - 🆕 Protection against infinite loops and circular dependencies

### Deployment & Operations
- **[Hourly Scraping](docs/hourly-scraping.md)** - Automated hourly job scraping with source rotation
- **[Deployment Guide](docs/deployment.md)** - Docker deployment with Portainer
- **[Environment Configuration](docs/guides/environments.md)** - Multi-environment setup (staging/production)
- **[Local Testing](docs/guides/local-testing.md)** - Docker local testing guide

### Integration & Planning
- **[Frontend Integration](docs/integrations/frontend.md)** - Integrate with job-finder-FE frontend application
- **[Next Steps](docs/next-steps.md)** - Roadmap, technical debt, and planned features

See **[docs/README.md](docs/README.md)** for complete documentation navigation.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Security

See [SECURITY.md](SECURITY.md) for security considerations and responsible disclosure.

## License

MIT - See [LICENSE](LICENSE) for details.

**Note**: The MIT license applies to the code, not to any data scraped using this tool. Users are responsible for compliance with data protection laws and website Terms of Service.
