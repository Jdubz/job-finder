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



def get_scheduler_settings_config() -> Dict[str, Any]:
    """Get scheduler settings for cron-based scraping."""
    return {
        # Enable/disable the scheduler
        "enabled": False,  # Disabled by default - enable when ready
        # Cron schedule (for reference - actual cron is set in crontab file)
        # Examples:
        #   "0 */6 * * *"   = Every 6 hours
        #   "0 8,14,20 * * *" = At 8am, 2pm, 8pm
        #   "0 * * * *"     = Every hour
        "cron_schedule": "0 */6 * * *",
        # Daytime hours when scraping should actually run (24-hour format)
        # Cron may trigger, but scraping only happens within these hours
        "daytime_hours": {
            "start": 6,   # 6am
            "end": 22,    # 10pm
        },
        # Timezone for daytime hours check
        "timezone": "America/Los_Angeles",
        # Scrape settings
        "target_matches": 5,      # Stop after finding this many potential matches
        "max_sources": 10,        # Maximum sources to scrape per run
        "min_match_score": 80,    # Minimum AI match score to consider
        # Metadata
        "updatedAt": datetime.utcnow().isoformat(),
        "updatedBy": "setup_script",
        "description": "Controls automated job scraping via cron. Set enabled=true to enable.",
    }


def get_ai_settings_config() -> Dict[str, Any]:
    """Get AI matching settings."""
    return {
        "provider": "claude",
        "model": "claude-3-5-haiku-20241022",  # Haiku for cost-effective processing
        "minMatchScore": 80,
        "costBudgetDaily": 50.0,
        # Model-specific settings
        "models": {
            # === Claude Models ===
            # Haiku - Fast & cost-effective
            "claude-3-5-haiku-20241022": {
                "maxTokens": 4096,  # Haiku's maximum output token limit
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.001,  # $1 per MTok input
                "cost_per_1k_output": 0.005,  # $5 per MTok output
            },
            "claude-3-haiku-20240307": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.00025,
                "cost_per_1k_output": 0.00125,
            },
            # Sonnet - Balanced performance & cost
            "claude-3-5-sonnet-20241022": {
                "maxTokens": 8000,  # Sonnet supports up to 8192
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.003,  # $3 per MTok input
                "cost_per_1k_output": 0.015,  # $15 per MTok output
            },
            "claude-3-5-sonnet-20240620": {
                "maxTokens": 8000,
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
            },
            "claude-3-sonnet-20240229": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.003,
                "cost_per_1k_output": 0.015,
            },
            # Opus - Most capable, highest cost
            "claude-3-opus-20240229": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.015,  # $15 per MTok input
                "cost_per_1k_output": 0.075,  # $75 per MTok output
            },
            "claude-opus-4-20250514": {
                "maxTokens": 8000,  # Opus 4 supports up to 16384
                "temperature": 0.3,
                "provider": "claude",
                "cost_per_1k_input": 0.015,
                "cost_per_1k_output": 0.075,
            },
            # === OpenAI Models ===
            # GPT-4 Turbo
            "gpt-4-turbo": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.01,  # $10 per MTok input
                "cost_per_1k_output": 0.03,  # $30 per MTok output
            },
            "gpt-4-turbo-2024-04-09": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.01,
                "cost_per_1k_output": 0.03,
            },
            # GPT-4o - Latest multimodal
            "gpt-4o": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.005,  # $5 per MTok input
                "cost_per_1k_output": 0.015,  # $15 per MTok output
            },
            "gpt-4o-2024-11-20": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.0025,  # $2.50 per MTok input
                "cost_per_1k_output": 0.01,  # $10 per MTok output
            },
            "gpt-4o-2024-08-06": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.0025,
                "cost_per_1k_output": 0.01,
            },
            # GPT-4o Mini - Most cost-effective
            "gpt-4o-mini": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.00015,  # $0.15 per MTok input
                "cost_per_1k_output": 0.0006,  # $0.60 per MTok output
            },
            "gpt-4o-mini-2024-07-18": {
                "maxTokens": 4096,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.00015,
                "cost_per_1k_output": 0.0006,
            },
            # Legacy GPT-4
            "gpt-4": {
                "maxTokens": 8000,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.03,  # $30 per MTok input
                "cost_per_1k_output": 0.06,  # $60 per MTok output
            },
            "gpt-4-0613": {
                "maxTokens": 8000,
                "temperature": 0.3,
                "provider": "openai",
                "cost_per_1k_input": 0.03,
                "cost_per_1k_output": 0.06,
            },
        },
        # Fallback settings if model not in models map
        "maxTokens": 4096,  # Conservative default
        "temperature": 0.3,
        # Scoring preferences
        "portlandOfficeBonus": 15,
        "userTimezone": -8,  # Pacific Time
        "preferLargeCompanies": True,
        "updatedAt": datetime.utcnow().isoformat(),
        "updatedBy": "setup_script",
    }


def setup_firestore_config(database_name: str = DATABASE_NAME):
    """
    Setup all Firestore configuration documents.
    
    Only creates documents that don't already exist to prevent overwriting.

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
        "scheduler-settings": get_scheduler_settings_config(),
    }

    created_count = 0
    skipped_count = 0
    
    for doc_name, config in configs.items():
        doc_ref = collection.document(doc_name)
        
        # Check if document already exists
        if doc_ref.get().exists:
            logger.info(f"  ⊘ {doc_name} already exists - skipping")
            skipped_count += 1
            continue
        
        # Create new document
        logger.info(f"  Creating {doc_name}...")
        doc_ref.set(config)
        logger.info(f"  ✓ {doc_name} created successfully")
        created_count += 1
    
    # Summary of operations
    logger.info(f"\n📊 Operations summary:")
    logger.info(f"  Created: {created_count}")
    logger.info(f"  Skipped (already exist): {skipped_count}")
    
    # Only show detailed summary if we created documents
    if created_count == 0:
        logger.info("\n⚠️  No new configurations created - all documents already exist")
        logger.info("     To update existing configs, edit them in Firestore Console")
        return

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

    # Scheduler Settings Summary
    scheduler_settings = configs["scheduler-settings"]
    logger.info("\n⏰ Scheduler Settings:")
    logger.info(f"  Enabled: {'✓ YES' if scheduler_settings['enabled'] else '✗ NO (DISABLED)'}")
    logger.info(f"  Cron Schedule: {scheduler_settings['cron_schedule']}")
    logger.info(f"  Daytime Hours: {scheduler_settings['daytime_hours']['start']}:00 - {scheduler_settings['daytime_hours']['end']}:00 {scheduler_settings['timezone']}")
    logger.info(f"  Target Matches: {scheduler_settings['target_matches']} per run")
    logger.info(f"  Max Sources: {scheduler_settings['max_sources']} per run")

    logger.info("\n" + "=" * 70)
    logger.info("✅ Configuration setup complete!")
    logger.info("=" * 70)
    logger.info("\nYou can now:")
    logger.info("1. Edit these configurations in Firestore Console")
    logger.info("2. Or use the job-finder-FE web UI to manage them")
    logger.info("3. Set scheduler-settings.enabled=true to ENABLE automated scraping")
    logger.info(
        f"4. View at: https://console.firebase.google.com/project/static-sites-257923/firestore/databases/{database_name}/data/~2Fjob-finder-config"
    )


if __name__ == "__main__":
    import sys
    
    # Setup both staging and production databases
    databases = ["portfolio-staging", "portfolio"]
    
    logger.info("=" * 70)
    logger.info("SETTING UP SCHEDULER CONFIGURATION FOR BOTH DATABASES")
    logger.info("=" * 70)
    logger.info("\nThis will create scheduler-settings (and other configs) in:")
    for db in databases:
        logger.info(f"  - {db}")
    logger.info("\n⚠️  SAFETY: Only creates configs that don't already exist")
    logger.info("   Existing configurations will NOT be overwritten")
    logger.info("\nScheduler will be DISABLED by default (enabled=false)")
    logger.info("Set enabled=true in Firestore when ready to activate\n")
    
    # Prompt for confirmation
    response = input("Continue? (yes/no): ").strip().lower()
    if response not in ["yes", "y"]:
        logger.info("Setup cancelled.")
        sys.exit(0)
    
    # Setup each database
    for database_name in databases:
        logger.info("\n" + "=" * 70)
        logger.info(f"Setting up: {database_name}")
        logger.info("=" * 70)
        setup_firestore_config(database_name)
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ ALL DATABASES CONFIGURED")
    logger.info("=" * 70)
    logger.info("\nScheduler status: DISABLED in both databases")
    logger.info("To enable:")
    logger.info("  1. Go to Firebase Console")
    logger.info("  2. Navigate to job-finder-config/scheduler-settings")
    logger.info("  3. Set enabled=true")
    logger.info("  4. Save changes")

