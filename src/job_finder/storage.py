"""Storage handlers for job postings."""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any


class JobStorage:
    """Handle storage of job postings in various formats."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize storage with configuration."""
        self.config = config
        self.output_format = config.get("output", {}).get("format", "json")
        self.file_path = config.get("output", {}).get("file_path", "data/jobs.json")

    def save(self, jobs: List[Dict[str, Any]]) -> None:
        """
        Save jobs to configured storage.

        Args:
            jobs: List of job postings to save.
        """
        if self.output_format == "json":
            self._save_json(jobs)
        elif self.output_format == "csv":
            self._save_csv(jobs)
        elif self.output_format == "database":
            self._save_database(jobs)
        else:
            raise ValueError(f"Unsupported output format: {self.output_format}")

    def _save_json(self, jobs: List[Dict[str, Any]]) -> None:
        """Save jobs as JSON."""
        Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w") as f:
            json.dump(jobs, f, indent=2)

    def _save_csv(self, jobs: List[Dict[str, Any]]) -> None:
        """Save jobs as CSV."""
        if not jobs:
            return

        Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.file_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=jobs[0].keys())
            writer.writeheader()
            writer.writerows(jobs)

    def _save_database(self, jobs: List[Dict[str, Any]]) -> None:
        """Save jobs to database."""
        # TODO: Implement database storage using SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
