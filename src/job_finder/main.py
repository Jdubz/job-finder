"""Main entry point for the job finder application."""
import argparse
import yaml
from pathlib import Path
from typing import Dict, Any

from job_finder.filters import JobFilter
from job_finder.storage import JobStorage


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def main() -> None:
    """Main execution function."""
    parser = argparse.ArgumentParser(description="Job Finder - Scrape and filter job postings")
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to configuration file (default: config/config.yaml)"
    )
    parser.add_argument(
        "--output",
        help="Override output file path from config"
    )
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)

    if args.output:
        config["output"]["file_path"] = args.output

    print("Starting job scraper...")

    # TODO: Initialize and run scrapers for each enabled site
    # scrapers = initialize_scrapers(config)
    # all_jobs = []
    # for scraper in scrapers:
    #     jobs = scraper.scrape()
    #     all_jobs.extend(jobs)

    all_jobs = []  # Placeholder

    # Filter jobs
    job_filter = JobFilter(config)
    filtered_jobs = job_filter.filter_jobs(all_jobs)

    print(f"Found {len(all_jobs)} jobs, {len(filtered_jobs)} after filtering")

    # Save results
    storage = JobStorage(config)
    storage.save(filtered_jobs)

    print(f"Results saved to {config['output']['file_path']}")


if __name__ == "__main__":
    main()
