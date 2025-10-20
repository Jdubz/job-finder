"""Unit tests for SmokeTestRunner."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Add src to path for imports - noqa: E402
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from scripts.smoke.queue_pipeline_smoke import SmokeTestRunner  # noqa: E402


@pytest.fixture
def temp_fixtures_dir():
    """Create temporary fixtures directory with sample fixtures."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fixtures_dir = Path(tmpdir) / "fixtures"
        fixtures_dir.mkdir()

        # Create sample fixture
        fixture = {
            "title": "Software Engineer",
            "company": "TestCo",
            "company_website": "https://testco.example.com",
            "location": "Remote",
            "description": "Test job description",
            "url": "https://testco.example.com/jobs/123",
            "posted_date": "2025-10-20",
            "salary": "$100,000 - $150,000",
        }

        fixture_file = fixtures_dir / "test_job.json"
        with open(fixture_file, "w") as f:
            json.dump(fixture, f)

        yield fixtures_dir


@pytest.fixture
def temp_output_dir():
    """Create temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestSmokeTestRunner:
    """Test SmokeTestRunner functionality."""

    def test_init_dry_run(self, temp_fixtures_dir, temp_output_dir):
        """Test initialization in dry-run mode."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        assert runner.env == "staging"
        assert runner.dry_run is True
        assert runner.database_name == "portfolio-staging"
        assert runner.queue_manager is None  # Not initialized in dry-run
        assert runner.job_storage is None
        assert runner.scraper_intake is None

    def test_init_determines_database_name(self, temp_fixtures_dir, temp_output_dir):
        """Test database name determination from environment."""
        runner = SmokeTestRunner(
            env="production",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        assert runner.database_name == "portfolio"

        runner = SmokeTestRunner(
            env="local",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        assert runner.database_name == "portfolio-staging"

    def test_load_fixtures(self, temp_fixtures_dir, temp_output_dir):
        """Test loading fixtures from directory."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        fixtures = runner.load_fixtures()

        assert len(fixtures) == 1
        assert fixtures[0]["title"] == "Software Engineer"
        assert fixtures[0]["company"] == "TestCo"
        assert "_fixture_file" in fixtures[0]
        assert fixtures[0]["_fixture_file"] == "test_job.json"

    def test_load_fixtures_missing_directory(self, temp_output_dir):
        """Test error handling for missing fixtures directory."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir="/nonexistent/path",
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        with pytest.raises(FileNotFoundError):
            runner.load_fixtures()

    def test_load_fixtures_invalid_json(self, temp_fixtures_dir, temp_output_dir):
        """Test handling of invalid JSON fixtures."""
        # Create invalid JSON file
        invalid_file = temp_fixtures_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        fixtures = runner.load_fixtures()

        # Should skip invalid file and load valid one
        assert len(fixtures) == 1
        assert fixtures[0]["title"] == "Software Engineer"

    def test_load_fixtures_missing_required_fields(self, temp_fixtures_dir, temp_output_dir):
        """Test handling of fixtures with missing required fields."""
        # Create fixture missing required fields
        incomplete_fixture = {
            "title": "Incomplete Job",
            "company": "BadCo",
            # Missing: company_website, location, description, url
        }

        incomplete_file = temp_fixtures_dir / "incomplete.json"
        with open(incomplete_file, "w") as f:
            json.dump(incomplete_fixture, f)

        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        fixtures = runner.load_fixtures()

        # Should skip incomplete fixture
        assert len(fixtures) == 1
        assert fixtures[0]["title"] == "Software Engineer"

    def test_submit_jobs_dry_run(self, temp_fixtures_dir, temp_output_dir):
        """Test job submission in dry-run mode."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        jobs = runner.load_fixtures()
        count = runner.submit_jobs(jobs)

        # In dry-run, should return count but not actually submit
        assert count == len(jobs)
        assert len(runner.submitted_jobs) == 0

    def test_validate_results_no_duplicates(self, temp_fixtures_dir, temp_output_dir):
        """Test validation passes with no duplicate URLs."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        results = [
            {"url": "https://example.com/job/1", "status": "SUCCESS"},
            {"url": "https://example.com/job/2", "status": "SUCCESS"},
        ]

        validation = runner.validate_results(results)

        assert validation["passed"] is True
        assert validation["checks"]["duplicate_urls"]["passed"] is True

    def test_validate_results_detects_duplicates(self, temp_fixtures_dir, temp_output_dir):
        """Test validation detects duplicate URLs."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        results = [
            {"url": "https://example.com/job/1", "status": "SUCCESS"},
            {"url": "https://example.com/job/1/", "status": "SUCCESS"},  # Same after normalization
        ]

        validation = runner.validate_results(results)

        assert validation["passed"] is False
        assert validation["checks"]["duplicate_urls"]["passed"] is False
        assert len(validation["checks"]["duplicate_urls"]["details"]) > 0

    def test_generate_report(self, temp_fixtures_dir, temp_output_dir):
        """Test report generation."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        # Load fixtures to set submitted_jobs
        jobs = runner.load_fixtures()
        runner.submitted_jobs = jobs

        results = [
            {
                "url": "https://testco.example.com/jobs/123",
                "doc_id": "doc123",
                "status": "SUCCESS",
                "company_name": "TestCo",
                "elapsed_seconds": 45.5,
            }
        ]

        validation_report = {
            "passed": True,
            "issues": [],
            "checks": {
                "duplicate_urls": {"passed": True, "details": []},
                "scoring_fields": {"passed": True, "details": []},
                "document_references": {"passed": True, "details": []},
            },
        }

        markdown_path, json_path = runner.generate_report(results, validation_report)

        # Check files were created
        assert Path(markdown_path).exists()
        assert Path(json_path).exists()

        # Verify markdown content
        with open(markdown_path, "r") as f:
            markdown_content = f.read()
            assert "Queue Pipeline Smoke Test Report" in markdown_content
            assert "staging" in markdown_content
            assert "TestCo" in markdown_content
            assert "✅ PASSED" in markdown_content

        # Verify JSON content
        with open(json_path, "r") as f:
            json_content = json.load(f)
            assert json_content["metadata"]["environment"] == "staging"
            assert json_content["summary"]["total_jobs"] == 1
            assert json_content["validation"]["passed"] is True
            assert len(json_content["results"]) == 1

    def test_generate_report_with_failures(self, temp_fixtures_dir, temp_output_dir):
        """Test report generation with validation failures."""
        runner = SmokeTestRunner(
            env="staging",
            fixtures_dir=str(temp_fixtures_dir),
            output_dir=str(temp_output_dir),
            dry_run=True,
        )

        runner.submitted_jobs = runner.load_fixtures()

        results = [
            {
                "url": "https://testco.example.com/jobs/123",
                "doc_id": "doc123",
                "status": "FAILED",
                "company_name": "TestCo",
                "elapsed_seconds": 10.0,
            }
        ]

        validation_report = {
            "passed": False,
            "issues": ["Missing scoring fields"],
            "checks": {
                "duplicate_urls": {"passed": True, "details": []},
                "scoring_fields": {"passed": False, "details": ["Missing matchScore in TestCo"]},
                "document_references": {"passed": True, "details": []},
            },
        }

        markdown_path, json_path = runner.generate_report(results, validation_report)

        # Verify markdown shows failure
        with open(markdown_path, "r") as f:
            markdown_content = f.read()
            assert "❌ FAILED" in markdown_content
            assert "Missing matchScore" in markdown_content


class TestSmokeTestHelpers:
    """Test helper functions used by smoke tests."""

    def test_normalize_url_consistency(self):
        """Test URL normalization is consistent."""
        from job_finder.utils.url_utils import normalize_url

        url1 = "https://example.com/job/123"
        url2 = "https://example.com/job/123/"
        url3 = "https://EXAMPLE.COM/job/123?utm_source=test"

        normalized1 = normalize_url(url1)
        normalized2 = normalize_url(url2)
        normalized3 = normalize_url(url3)

        assert normalized1 == normalized2 == normalized3
