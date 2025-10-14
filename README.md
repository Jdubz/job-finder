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

- Scrapes multiple job boards (LinkedIn, Indeed, etc.)
- Filters jobs based on your keywords, experience, and location preferences
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

3. **Configure your preferences:**
   ```bash
   cp config/config.example.yaml config/config.yaml
   # Edit config/config.yaml with your job search criteria
   ```

4. **Set up environment variables (optional):**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials if needed
   ```

## Usage

Run the scraper with default configuration:
```bash
python -m job_finder.main
```

Use a custom configuration file:
```bash
python -m job_finder.main --config path/to/config.yaml
```

Override output location:
```bash
python -m job_finder.main --output data/my_jobs.json
```

## Development

Install development dependencies:
```bash
pip install -r requirements.txt
pip install -e ".[dev]"
```

Run tests:
```bash
pytest
```

Format code:
```bash
black src/ tests/
```

Run linter:
```bash
flake8 src/ tests/
```

Type checking:
```bash
mypy src/
```

## Project Structure

```
job-finder/
├── src/job_finder/        # Main package
│   ├── scrapers/          # Site-specific scrapers
│   ├── filters.py         # Job filtering logic
│   ├── storage.py         # Data storage handlers
│   └── main.py            # Entry point
├── tests/                 # Test suite
├── config/                # Configuration files
├── data/                  # Output data directory
└── logs/                  # Application logs
```

## Responsible Use Guidelines

### Before You Start

1. **Review Terms of Service**: Check each job board's ToS to ensure scraping is allowed
2. **Check robots.txt**: Verify that automated access is permitted
3. **Use Appropriate Rate Limiting**: Respect server resources with reasonable delays
4. **Personal Use Only**: Do not use for commercial purposes or data resale
5. **Respect Privacy**: Handle any collected data responsibly and in compliance with regulations

### What NOT to Do

- Do not use for bulk data harvesting or commercial purposes
- Do not circumvent rate limits or access controls
- Do not use for credential testing or unauthorized access
- Do not scrape sites that explicitly prohibit automated access
- Do not share or sell scraped data

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## Security

See [SECURITY.md](SECURITY.md) for security considerations and responsible disclosure.

## License

MIT - See [LICENSE](LICENSE) for details.

**Note**: The MIT license applies to the code, not to any data scraped using this tool. Users are responsible for compliance with data protection laws and website Terms of Service.
