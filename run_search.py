#!/usr/bin/env python3
"""Run job search with the orchestrator."""

import sys
from pathlib import Path

import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from job_finder.logging_config import setup_logging
from job_finder.search_orchestrator import JobSearchOrchestrator

# Set up logging
setup_logging()

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Override max_jobs to 30 for this run
config["search"]["max_jobs"] = 30

# Run search
orchestrator = JobSearchOrchestrator(config)
stats = orchestrator.run_search()

# Print summary
print("\n" + "=" * 70)
print("SEARCH COMPLETE!")
print("=" * 70)
print(f"Jobs saved: {stats['jobs_saved']}")
print(f"Jobs matched: {stats['jobs_matched']}")
print(f"Jobs analyzed: {stats['jobs_analyzed']}")
print("=" * 70)
