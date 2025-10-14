#!/usr/bin/env python3
"""Run a full job search using configured sources."""
import os
import yaml
import logging
from dotenv import load_dotenv
from job_finder.search_orchestrator import JobSearchOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

# Load environment variables
load_dotenv()

print("=" * 70)
print("JOB SEARCH - FULL PIPELINE")
print("=" * 70)

# Load configuration
config_path = "config/config.yaml"
print(f"\n📋 Loading configuration from: {config_path}")

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

print(f"✓ Configuration loaded")
print(f"  - Profile source: {config.get('profile', {}).get('source')}")
print(f"  - Storage database: {config.get('storage', {}).get('database_name')}")
print(f"  - Max jobs: {config.get('search', {}).get('max_jobs')}")
print(f"  - Remote only: {config.get('search', {}).get('remote_only')}")
print(f"  - Min match score: {config.get('ai', {}).get('min_match_score')}")

# Create and run orchestrator
orchestrator = JobSearchOrchestrator(config)

try:
    stats = orchestrator.run_search()

    print("\n" + "=" * 70)
    print("🎉 JOB SEARCH COMPLETED SUCCESSFULLY!")
    print("=" * 70)
    print(f"\nTo view your job matches:")
    print(f"  1. Open Firebase Console")
    print(f"  2. Navigate to Firestore Database")
    print(f"  3. Select database: {config.get('storage', {}).get('database_name')}")
    print(f"  4. View collection: job-matches")
    print(f"\nSaved {stats['jobs_saved']} job matches ready for document generation!")

except Exception as e:
    print(f"\n❌ Error during job search: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)
