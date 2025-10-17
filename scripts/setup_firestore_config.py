#!/usr/bin/env python3
"""
Setup Firestore configuration for job-finder.

Creates the job-finder-config collection with:
- job-filters: Strike-based filtering rules
- technology-ranks: Technology preferences
- stop-list: Basic exclusions (legacy, but kept for compatibility)
- queue-settings: Queue processing configuration
- ai-settings: AI matching configuration
"""

import logging
from datetime import datetime
from typing import Dict, Any

from job_finder.storage.firestore_client import FirestoreClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_NAME = "portfolio-staging"
CREDENTIALS_PATH = ".firebase/static-sites-257923-firebase-adminsdk.json"


def get_job_filters_config() -> Dict[str, Any]:
    """Get job filters configuration with strike-based system."""
    return {
        "enabled": True,
        "strikeThreshold": 5,
        # Hard Rejections (immediate fail)
        "hardRejections": {
            "excludedJobTypes": [
                "sales",
                "hr",
                "human resources",
                "people operations",
                "talent acquisition",
                "recruiter",
                "recruiting",
                "support",
                "customer success",
            ],
            "excludedSeniority": [
                "associate",
                "junior",
                "intern",
                "entry-level",
                "entry level",
                "co-op",
            ],
            "excludedCompanies": [],  # Managed via company profiles
            "excludedKeywords": [
                "clearance required",
                "security clearance",
                "relocation required",
                "must relocate",
            ],
            "minSalaryFloor": 100000,
            "rejectCommissionOnly": True,
        },
        # Remote Policy (hard rejection if violated)
        "remotePolicy": {
            "allowRemote": True,
            "allowHybridPortland": True,
            "allowOnsite": False,
        },
        # Strike: Salary
        "salaryStrike": {
            "enabled": True,
            "threshold": 150000,
            "points": 2,
        },
        # Strike: Experience
        "experienceStrike": {
            "enabled": True,
            "minPreferred": 6,
            "points": 1,
        },
        # Strike: Seniority
        "seniorityStrikes": {
            "mid-level": 2,
            "mid level": 2,
            "principal": 1,
            "director": 1,
            "manager": 1,
            "engineering manager": 1,
        },
        # Strike: Quality
        "qualityStrikes": {
            "minDescriptionLength": 200,
            "shortDescriptionPoints": 1,
            "buzzwords": ["rockstar", "ninja", "guru", "10x engineer", "code wizard"],
            "buzzwordPoints": 1,
        },
        # Strike: Age
        "ageStrike": {
            "enabled": True,
            "strikeDays": 1,  # > 1 day = strike
            "rejectDays": 7,  # > 7 days = hard reject
            "points": 1,
        },
        # Metadata
        "lastUpdated": datetime.utcnow().isoformat(),
        "version": "2.0-strike-system",
    }


def get_technology_ranks_config() -> Dict[str, Any]:
    """Get technology ranking configuration."""
    return {
        "technologies": {
            # Required (must have at least one)
            "Python": {"rank": "required", "points": 0, "mentions": 0},
            "TypeScript": {"rank": "required", "points": 0, "mentions": 0},
            "JavaScript": {"rank": "required", "points": 0, "mentions": 0},
            "React": {"rank": "required", "points": 0, "mentions": 0},
            "Angular": {"rank": "required", "points": 0, "mentions": 0},
            "Node.js": {"rank": "required", "points": 0, "mentions": 0},
            "GCP": {"rank": "required", "points": 0, "mentions": 0},
            "Google Cloud": {"rank": "required", "points": 0, "mentions": 0},
            "Kubernetes": {"rank": "required", "points": 0, "mentions": 0},
            "Docker": {"rank": "required", "points": 0, "mentions": 0},
            # OK (neutral)
            "C++": {"rank": "ok", "points": 0, "mentions": 0},
            "Go": {"rank": "ok", "points": 0, "mentions": 0},
            "Rust": {"rank": "ok", "points": 0, "mentions": 0},
            "PostgreSQL": {"rank": "ok", "points": 0, "mentions": 0},
            "MySQL": {"rank": "ok", "points": 0, "mentions": 0},
            "MongoDB": {"rank": "ok", "points": 0, "mentions": 0},
            "Redis": {"rank": "ok", "points": 0, "mentions": 0},
            # Strike (prefer to avoid)
            "Java": {"rank": "strike", "points": 2, "mentions": 0},
            "PHP": {"rank": "strike", "points": 2, "mentions": 0},
            "Ruby": {"rank": "strike", "points": 2, "mentions": 0},
            "Rails": {"rank": "strike", "points": 2, "mentions": 0},
            "Ruby on Rails": {"rank": "strike", "points": 2, "mentions": 0},
            "WordPress": {"rank": "strike", "points": 2, "mentions": 0},
            ".NET": {"rank": "strike", "points": 2, "mentions": 0},
            "C#": {"rank": "strike", "points": 2, "mentions": 0},
            "Perl": {"rank": "strike", "points": 2, "mentions": 0},
        },
        "strikes": {
            "missingAllRequired": 1,
            "perBadTech": 2,
        },
        "lastUpdated": datetime.utcnow().isoformat(),
        "extractedFromJobs": 0,
        "version": "1.0",
    }


def get_stop_list_config() -> Dict[str, Any]:
    """Get stop list configuration (legacy, mostly handled by job-filters now)."""
    return {
        "excludedCompanies": [],
        "excludedKeywords": [
            "clearance required",
            "security clearance",
            "relocation required",
            "must relocate",
        ],
        "excludedDomains": [],
        "updatedAt": datetime.utcnow().isoformat(),
        "updatedBy": "setup_script",
    }


def get_queue_settings_config() -> Dict[str, Any]:
    """Get queue processing settings."""
    return {
        "maxRetries": 3,
        "retryDelaySeconds": 60,
        "processingTimeout": 300,
        "updatedAt": datetime.utcnow().isoformat(),
        "updatedBy": "setup_script",
    }


def get_ai_settings_config() -> Dict[str, Any]:
    """Get AI matching settings."""
    return {
        "provider": "claude",
        "model": "claude-3-5-sonnet-20241022",
        "minMatchScore": 80,
        "costBudgetDaily": 50.0,
        "updatedAt": datetime.utcnow().isoformat(),
        "updatedBy": "setup_script",
    }


def setup_firestore_config(database_name: str = DATABASE_NAME):
    """
    Setup all Firestore configuration documents.

    Args:
        database_name: Name of the Firestore database
    """
    logger.info(f"Setting up Firestore configuration in database: {database_name}")

    db = FirestoreClient.get_client(database_name, CREDENTIALS_PATH)
    collection = db.collection("job-finder-config")

    configs = {
        "job-filters": get_job_filters_config(),
        "technology-ranks": get_technology_ranks_config(),
        "stop-list": get_stop_list_config(),
        "queue-settings": get_queue_settings_config(),
        "ai-settings": get_ai_settings_config(),
    }

    for doc_name, config in configs.items():
        logger.info(f"  Writing {doc_name}...")
        doc_ref = collection.document(doc_name)
        doc_ref.set(config)
        logger.info(f"  ✓ {doc_name} written successfully")

    logger.info("\n" + "=" * 70)
    logger.info("CONFIGURATION SUMMARY")
    logger.info("=" * 70)

    # Job Filters Summary
    job_filters = configs["job-filters"]
    logger.info("\n📋 Job Filters:")
    logger.info(f"  Strike Threshold: {job_filters['strikeThreshold']}")
    logger.info(
        f"  Excluded Job Types: {len(job_filters['hardRejections']['excludedJobTypes'])} types"
    )
    logger.info(
        f"  Excluded Seniority: {len(job_filters['hardRejections']['excludedSeniority'])} levels"
    )
    logger.info(f"  Min Salary Floor: ${job_filters['hardRejections']['minSalaryFloor']:,}")
    logger.info(
        f"  Remote Policy: {'✓' if job_filters['remotePolicy']['allowRemote'] else '✗'} Remote, "
        f"{'✓' if job_filters['remotePolicy']['allowHybridPortland'] else '✗'} Hybrid (Portland), "
        f"{'✓' if job_filters['remotePolicy']['allowOnsite'] else '✗'} Onsite"
    )

    # Technology Ranks Summary
    tech_ranks = configs["technology-ranks"]
    required_techs = [
        name for name, cfg in tech_ranks["technologies"].items() if cfg["rank"] == "required"
    ]
    strike_techs = [
        name for name, cfg in tech_ranks["technologies"].items() if cfg["rank"] == "strike"
    ]

    logger.info("\n🔧 Technology Ranks:")
    logger.info(f"  Required (need ≥1): {len(required_techs)} technologies")
    logger.info(f"    {', '.join(required_techs[:5])}...")
    logger.info(f"  Strike (avoid): {len(strike_techs)} technologies")
    logger.info(f"    {', '.join(strike_techs[:5])}...")

    # AI Settings Summary
    ai_settings = configs["ai-settings"]
    logger.info("\n🤖 AI Settings:")
    logger.info(f"  Provider: {ai_settings['provider']}")
    logger.info(f"  Model: {ai_settings['model']}")
    logger.info(f"  Min Match Score: {ai_settings['minMatchScore']}")

    logger.info("\n" + "=" * 70)
    logger.info("✅ Configuration setup complete!")
    logger.info("=" * 70)
    logger.info("\nYou can now:")
    logger.info("1. Edit these configurations in Firestore Console")
    logger.info("2. Or use the Portfolio web UI to manage them")
    logger.info(
        f"3. View at: https://console.firebase.google.com/project/static-sites-257923/firestore/databases/{database_name}/data/~2Fjob-finder-config"
    )


if __name__ == "__main__":
    setup_firestore_config()
