# Contributing to Job Finder

Thank you for your interest in contributing to Job Finder! This document provides guidelines for contributing to the project.

## Code of Conduct

Please be respectful and constructive in all interactions with the community.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear description of the problem
- Steps to reproduce the issue
- Expected vs actual behavior
- Your environment (OS, Python version, etc.)

### Suggesting Features

Feature suggestions are welcome! Please create an issue describing:
- The problem your feature would solve
- How you envision the feature working
- Any alternative solutions you've considered

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and ensure they pass (`pytest`)
5. Format your code (`black src/ tests/`)
6. Commit your changes with clear commit messages
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

#### Pull Request Guidelines

- Follow the existing code style (PEP 8, enforced by black and flake8)
- Add tests for new functionality
- Update documentation as needed
- Keep PRs focused on a single feature or fix
- Ensure all tests pass before submitting

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/job-finder.git
cd job-finder

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest
```

## Code Quality Standards

- **Code formatting**: Use `black` with line length of 100
- **Linting**: Code should pass `flake8` checks
- **Type hints**: All functions should have type hints (checked with `mypy`)
- **Tests**: Maintain test coverage above 80%
- **Documentation**: Update docstrings and README as needed

### Testing Naming Conventions

All test files must follow pytest's discovery patterns:

- **Test files**: Must start with `test_` (e.g., `test_ai_matcher.py`)
- **Test classes**: Must start with `Test` (e.g., `class TestAIMatcher`)
- **Test functions**: Must start with `test_` (e.g., `def test_analyze_match()`)

For detailed guidelines and examples, see [Testing Naming Conventions](docs/testing/naming-conventions.md).

To verify your tests will be discovered by pytest:
```bash
# Check if your tests are discovered
pytest --collect-only

# Generate test inventory report
python scripts/testing/list_tests.py
```

## Adding New Scrapers

When adding support for a new job site:

1. Create a new scraper file in `src/job_finder/scrapers/`
2. Inherit from `BaseScraper`
3. Implement required methods (`scrape()` and `parse_job()`)
4. Add comprehensive tests with mocked responses
5. Update configuration documentation
6. **IMPORTANT**: Verify the site's Terms of Service allows scraping
7. Respect robots.txt and implement appropriate rate limiting

## Legal and Ethical Guidelines

**IMPORTANT**: All contributions must comply with legal and ethical standards:

- Do not contribute code that violates website Terms of Service
- Respect robots.txt directives
- Implement appropriate rate limiting
- Do not contribute scrapers for sites that explicitly prohibit automated access
- Users are responsible for ensuring their use complies with applicable laws

## Questions?

If you have questions about contributing, feel free to open an issue with the "question" label.
