#!/usr/bin/env python3
"""Test script for the new architecture in staging."""

import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from job_finder.search_orchestrator import JobSearchOrchestrator  # noqa: E402

# Configuration for testing
config: Dict[str, Any] = {
    "profile": {
        "source": "firestore",
        "firestore": {
            "database_name": "portfolio",  # Production profile
            "name": "Justin Williams",
            "email": "justinwilliams901@gmail.com",
        },
    },
    "ai": {
        "enabled": True,
        "provider": "claude",
        "model": "claude-3-5-haiku-20241022",  # Fast & cost-effective
        "min_match_score": 80,
        "generate_intake_data": True,
        "portland_office_bonus": 15,
        "user_timezone": -8,
        "prefer_large_companies": True,
    },
    "storage": {
        "database_name": "portfolio-staging",  # Staging database
    },
    "search": {
        "max_jobs": 3,  # Limit to 3 jobs for testing
    },
    "scraping": {
        "delay_between_requests": 1,
    },
    "filters": {
        "strict_role_filtering": True,
        "min_seniority_level": "senior",
    },
}

if __name__ == "__main__":
    print("=" * 70)
    print("TESTING NEW ARCHITECTURE IN STAGING")
    print("=" * 70)
    print(f"Profile: {config['profile']['firestore']['database_name']}")
    print(f"Storage: {config['storage']['database_name']}")
    print(f"Max jobs: {config['search']['max_jobs']}")
    print("=" * 70)

    orchestrator = JobSearchOrchestrator(config)
    stats: Dict[str, Any] = orchestrator.run_search()

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print(f"Sources scraped: {stats['sources_scraped']}")
    print(f"Jobs matched: {stats['jobs_matched']}")
    print(f"Jobs saved: {stats['jobs_saved']}")
    print(f"Errors: {len(stats['errors'])}")

    if stats["errors"]:
        print("\nErrors encountered:")
        for error in stats["errors"]:
            print(f"  - {error}")

    print("=" * 70)
