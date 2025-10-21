"""Tests for job storage module."""

import csv
import importlib.util
import json
import tempfile
from pathlib import Path

import pytest

# Import from the storage.py module file (not the storage/ package)
# The storage/ directory shadows storage.py, so we need to import directly
_spec = importlib.util.spec_from_file_location(
    "job_finder_storage_module",
    Path(__file__).parent.parent / "src" / "job_finder" / "storage.py",
)
_storage_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_storage_module)
JobStorage = _storage_module.JobStorage


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_jobs():
    """Create sample job data for testing."""
    return [
        {
            "title": "Senior Python Engineer",
            "company": "Tech Corp",
            "location": "Remote",
            "url": "https://example.com/job/1",
            "description": "Python developer position",
        },
        {
            "title": "JavaScript Developer",
            "company": "Web Inc",
            "location": "Portland, OR",
            "url": "https://example.com/job/2",
            "description": "JavaScript developer position",
        },
    ]


class TestJobStorageInit:
    """Test JobStorage initialization."""

    def test_init_default_format(self):
        """Test initialization with default format."""
        config = {"output": {"file_path": "data/jobs.json"}}
        storage = JobStorage(config)
        assert storage.output_format == "json"
        assert storage.file_path == "data/jobs.json"

    def test_init_explicit_json_format(self):
        """Test initialization with explicit JSON format."""
        config = {"output": {"format": "json", "file_path": "data/output.json"}}
        storage = JobStorage(config)
        assert storage.output_format == "json"
        assert storage.file_path == "data/output.json"

    def test_init_csv_format(self):
        """Test initialization with CSV format."""
        config = {"output": {"format": "csv", "file_path": "data/jobs.csv"}}
        storage = JobStorage(config)
        assert storage.output_format == "csv"
        assert storage.file_path == "data/jobs.csv"

    def test_init_database_format(self):
        """Test initialization with database format."""
        config = {"output": {"format": "database", "file_path": "data/jobs.db"}}
        storage = JobStorage(config)
        assert storage.output_format == "database"

    def test_init_minimal_config(self):
        """Test initialization with minimal config."""
        config = {}
        storage = JobStorage(config)
        assert storage.output_format == "json"
        assert storage.file_path == "data/jobs.json"


class TestJobStorageSaveJSON:
    """Test JSON storage functionality."""

    def test_save_json_basic(self, temp_dir, sample_jobs):
        """Test basic JSON save."""
        file_path = Path(temp_dir) / "jobs.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(sample_jobs)

        # Verify file exists
        assert file_path.exists()

        # Verify content
        with open(file_path) as f:
            saved_data = json.load(f)
        assert saved_data == sample_jobs

    def test_save_json_creates_parent_directory(self, temp_dir, sample_jobs):
        """Test that parent directories are created."""
        file_path = Path(temp_dir) / "subdir" / "nested" / "jobs.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(sample_jobs)

        # Verify file and directories exist
        assert file_path.exists()
        assert file_path.parent.exists()

    def test_save_json_empty_list(self, temp_dir):
        """Test saving empty job list."""
        file_path = Path(temp_dir) / "empty.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save([])

        # Verify file exists and contains empty list
        assert file_path.exists()
        with open(file_path) as f:
            saved_data = json.load(f)
        assert saved_data == []

    def test_save_json_overwrites_existing(self, temp_dir, sample_jobs):
        """Test that saving overwrites existing file."""
        file_path = Path(temp_dir) / "jobs.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        # Save first set of jobs
        storage.save(sample_jobs[:1])

        # Save second set of jobs (should overwrite)
        storage.save(sample_jobs)

        # Verify file contains second set
        with open(file_path) as f:
            saved_data = json.load(f)
        assert len(saved_data) == 2
        assert saved_data == sample_jobs

    def test_save_json_formatted(self, temp_dir, sample_jobs):
        """Test that JSON is formatted with indentation."""
        file_path = Path(temp_dir) / "jobs.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(sample_jobs)

        # Verify formatting
        with open(file_path) as f:
            content = f.read()
        # Indented JSON should have newlines
        assert "\n" in content
        assert "  " in content  # 2-space indent


class TestJobStorageSaveCSV:
    """Test CSV storage functionality."""

    def test_save_csv_basic(self, temp_dir, sample_jobs):
        """Test basic CSV save."""
        file_path = Path(temp_dir) / "jobs.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(sample_jobs)

        # Verify file exists
        assert file_path.exists()

        # Verify content
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["title"] == "Senior Python Engineer"
        assert rows[1]["title"] == "JavaScript Developer"

    def test_save_csv_headers(self, temp_dir, sample_jobs):
        """Test CSV headers match first job keys."""
        file_path = Path(temp_dir) / "jobs.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(sample_jobs)

        # Verify headers
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

        expected_headers = list(sample_jobs[0].keys())
        assert headers == expected_headers

    def test_save_csv_creates_parent_directory(self, temp_dir, sample_jobs):
        """Test that parent directories are created."""
        file_path = Path(temp_dir) / "subdir" / "jobs.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(sample_jobs)

        # Verify file and directories exist
        assert file_path.exists()
        assert file_path.parent.exists()

    def test_save_csv_empty_list(self, temp_dir):
        """Test saving empty job list does nothing."""
        file_path = Path(temp_dir) / "empty.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save([])

        # Verify file was not created (early return for empty list)
        assert not file_path.exists()

    def test_save_csv_overwrites_existing(self, temp_dir, sample_jobs):
        """Test that saving overwrites existing file."""
        file_path = Path(temp_dir) / "jobs.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        # Save first set
        storage.save(sample_jobs[:1])

        # Save second set (should overwrite)
        storage.save(sample_jobs)

        # Verify file contains second set
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2


class TestJobStorageSaveDatabase:
    """Test database storage (not implemented)."""

    def test_save_database_not_implemented(self, sample_jobs):
        """Test that database storage raises NotImplementedError."""
        config = {"output": {"format": "database", "file_path": "data/jobs.db"}}
        storage = JobStorage(config)

        with pytest.raises(NotImplementedError) as exc_info:
            storage.save(sample_jobs)

        assert "SQL database storage not supported" in str(exc_info.value)
        assert "Use Firestore" in str(exc_info.value)


class TestJobStorageInvalidFormat:
    """Test handling of invalid format."""

    def test_save_invalid_format(self, sample_jobs):
        """Test that invalid format raises ValueError."""
        config = {"output": {"format": "xml", "file_path": "data/jobs.xml"}}
        storage = JobStorage(config)

        with pytest.raises(ValueError) as exc_info:
            storage.save(sample_jobs)

        assert "Unsupported output format: xml" in str(exc_info.value)


class TestJobStorageEdgeCases:
    """Test edge cases and special scenarios."""

    def test_save_json_with_special_characters(self, temp_dir):
        """Test saving jobs with special characters."""
        jobs = [
            {
                "title": "Engineer (Senior)",
                "company": "Test & Co.",
                "description": 'Job with "quotes" and \n newlines',
                "url": "https://example.com/job?param=value&other=123",
            }
        ]
        file_path = Path(temp_dir) / "special.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(jobs)

        # Verify content preserved
        with open(file_path) as f:
            saved_data = json.load(f)
        assert saved_data == jobs

    def test_save_csv_with_special_characters(self, temp_dir):
        """Test saving CSV with special characters."""
        jobs = [
            {
                "title": "Engineer, Senior",
                "company": "Test & Co.",
                "description": 'Job with "quotes"',
            }
        ]
        file_path = Path(temp_dir) / "special.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(jobs)

        # Verify content preserved (CSV should handle escaping)
        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert rows[0]["title"] == "Engineer, Senior"
        assert rows[0]["company"] == "Test & Co."

    def test_save_json_single_job(self, temp_dir):
        """Test saving single job."""
        job = [{"title": "Engineer", "company": "Corp", "url": "https://example.com"}]
        file_path = Path(temp_dir) / "single.json"
        config = {"output": {"format": "json", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(job)

        with open(file_path) as f:
            saved_data = json.load(f)
        assert len(saved_data) == 1
        assert saved_data[0]["title"] == "Engineer"

    def test_save_csv_single_job(self, temp_dir):
        """Test saving single job as CSV."""
        job = [{"title": "Engineer", "company": "Corp"}]
        file_path = Path(temp_dir) / "single.csv"
        config = {"output": {"format": "csv", "file_path": str(file_path)}}
        storage = JobStorage(config)

        storage.save(job)

        with open(file_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["title"] == "Engineer"
